#!/usr/bin/env python
# (C) Copyright 2015-2017 Hewlett Packard Enterprise Development LP

# Core modules
import glob
import logging
import os
import pstats
import signal
import six
import sys
import time

# Custom modules
import checks.collector
import checks.services_checks as status_checks
import jmxfetch
import monasca_agent.common.config as cfg
import monasca_agent.common.daemon
import monasca_agent.common.emitter
import monasca_agent.common.util as util

# set up logging before importing any other components
util.initialize_logging('collector')
os.umask(0o22)

# Check we're not using an old version of Python. We need 2.4 above because
# some modules (like subprocess) were only introduced in 2.4.
if int(sys.version_info[1]) <= 3:
    sys.stderr.write("Monasca Agent requires python 2.4 or later.\n")
    sys.exit(2)

# Constants
PID_NAME = "monasca-agent"
START_COMMANDS = ['start', 'restart', 'foreground']

# Globals
log = logging.getLogger('collector')


# todo the collector has daemon code but is always run in foreground mode
# from the supervisor, is there a reason for the daemon code then?
class CollectorDaemon(monasca_agent.common.daemon.Daemon):

    """The agent class is a daemon that runs the collector in a background process.

    """

    def __init__(self, pidfile, autorestart, start_event=True):
        monasca_agent.common.daemon.Daemon.__init__(self, pidfile, autorestart=autorestart)
        self.run_forever = True
        self.collector = None
        self.start_event = start_event

    def _handle_sigterm(self, signum, frame):
        log.debug("Caught sigterm.")
        self._stop(0)
        sys.exit(0)

    def _handle_sigusr1(self, signum, frame):
        log.debug("Caught sigusrl.")
        self._stop(120)
        sys.exit(monasca_agent.common.daemon.AgentSupervisor.RESTART_EXIT_STATUS)

    def _stop(self, timeout=0):
        log.info("Stopping collector run loop.")
        self.run_forever = False

        if jmxfetch.JMXFetch.is_running():
            jmxfetch.JMXFetch.stop()

        if self.collector:
            self.collector.stop(timeout)

        log.info('collector stopped')

    def run(self, config):
        """Main loop of the collector.

        """
        # Gracefully exit on sigterm.
        signal.signal(signal.SIGTERM, self._handle_sigterm)

        # A SIGUSR1 signals an exit with an autorestart
        if hasattr(signal, 'SIGUSR1'):
            # Windows does not have this signal.
            signal.signal(signal.SIGUSR1, self._handle_sigusr1)

        # Handle Keyboard Interrupt
        signal.signal(signal.SIGINT, self._handle_sigterm)

        # Load the checks_d checks
        checksd = util.load_check_directory()

        self.collector = checks.collector.Collector(config, monasca_agent.common.emitter.http_emitter, checksd)

        check_frequency = int(config['check_freq'])

        # Initialize the auto-restarter
        self.restart_interval = int(util.get_collector_restart_interval())
        self.agent_start = time.time()

        exitCode = 0
        exitTimeout = 0

        # Run the main loop.
        while self.run_forever:
            collection_start = time.time()
            # enable profiler if needed
            profiled = False
            if config.get('profile', False):
                try:
                    import cProfile
                    profiler = cProfile.Profile()
                    profiled = True
                    profiler.enable()
                    log.debug("Agent profiling is enabled")
                except Exception:
                    log.warn("Cannot enable profiler")

            # Do the work.
            self.collector.run(check_frequency)

            # disable profiler and printout stats to stdout
            if config.get('profile', False) and profiled:
                try:
                    profiler.disable()
                    s = six.StringIO()
                    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
                    ps.print_stats()
                    log.debug(s.getvalue())
                except Exception:
                    log.warn("Cannot disable profiler")

            # Check if we should restart.
            if self.autorestart and self._should_restart():
                self.run_forever = False
                exitCode = monasca_agent.common.daemon.AgentSupervisor.RESTART_EXIT_STATUS
                exitTimeout = 120
                log.info('Startng an auto restart')

            # Only plan for the next loop if we will continue,
            # otherwise just exit quickly.
            if self.run_forever:
                collection_time = time.time() - collection_start
                if collection_time < check_frequency:
                    time.sleep(check_frequency - collection_time)
                else:
                    log.info("Collection took {0} which is as long or longer then the configured collection frequency "
                             "of {1}. Starting collection again without waiting in result.".format(collection_time,
                                                                                                   check_frequency))
        self._stop(exitTimeout)

        # Explicitly kill the process, because it might be running
        # as a daemon.
        log.info("Exiting collector daemon, code %d." % exitCode)
        os._exit(exitCode)

    def _should_restart(self):
        if time.time() - self.agent_start > self.restart_interval:
            return True
        return False


def main():
    options, args = util.get_parsed_args(prog='monasca-collector')
    config = cfg.Config()
    collector_config = config.get_config(['Main', 'Api', 'Logging'])
    autorestart = collector_config.get('autorestart', False)

    collector_restart_interval = collector_config.get(
        'collector_restart_interval', 24)
    if collector_restart_interval in range(1, 49):
        pass
    else:
        log.error("Collector_restart_interval = {0} is out of legal range"
                  " [1, 48]. Reset collector_restart_interval to 24".format(collector_restart_interval))
        collector_restart_interval = 24

    COMMANDS = [
        'start',
        'stop',
        'restart',
        'foreground',
        'status',
        'info',
        'check',
        'check_all',
        'configcheck',
        'jmx',
    ]

    if len(args) < 1:
        sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], "|".join(COMMANDS)))
        return 2

    command = args[0]
    if command not in COMMANDS:
        sys.stderr.write("Unknown command: %s\n" % command)
        return 3

    pid_file = util.PidFile('monasca-agent')

    if options.clean:
        pid_file.clean()

    agent = CollectorDaemon(pid_file.get_path(), autorestart)

    if command in START_COMMANDS:
        log.info('Agent version %s' % config.get_version())

    if 'start' == command:
        log.info('Start daemon')
        agent.start()

    elif 'stop' == command:
        log.info('Stop daemon')
        agent.stop()

    elif 'restart' == command:
        log.info('Restart daemon')
        agent.restart()

    elif 'status' == command:
        agent.status()

    elif 'info' == command:
        return agent.info(verbose=options.verbose)

    elif 'foreground' == command:
        logging.info('Running in foreground')
        if autorestart:
            # Set-up the supervisor callbacks and fork it.
            logging.info('Running Agent with auto-restart ON')
        # Run in the standard foreground.
        agent.run(collector_config)

    elif 'check' == command:
        check_name = args[1]
        checks = util.load_check_directory()
        for check in checks['initialized_checks']:
            if check.name == check_name:
                run_check(check)

    elif 'check_all' == command:
        print("Loading check directory...")
        checks = util.load_check_directory()
        print("...directory loaded.\n")
        for check in checks['initialized_checks']:
            run_check(check)

    elif 'configcheck' == command or 'configtest' == command:
        all_valid = True
        paths = util.Paths()
        for conf_path in glob.glob(os.path.join(paths.get_confd_path(), "*.yaml")):
            basename = os.path.basename(conf_path)
            try:
                config.check_yaml(conf_path)
            except Exception as e:
                all_valid = False
                print("%s contains errors:\n    %s" % (basename, e))
            else:
                print("%s is valid" % basename)
        if all_valid:
            print("All yaml files passed. You can now run the Monitoring agent.")
            return 0
        else:
            print("Fix the invalid yaml files above in order to start the Monitoring agent. "
                  "A useful external tool for yaml parsing can be found at "
                  "http://yaml-online-parser.appspot.com/")
            return 1

    elif 'jmx' == command:

        if len(args) < 2 or args[1] not in jmxfetch.JMX_LIST_COMMANDS.keys():
            print("#" * 80)
            print("JMX tool to be used to help configure your JMX checks.")
            print("See http://docs.datadoghq.com/integrations/java/ for more information")
            print("#" * 80)
            print("\n")
            print("You have to specify one of the following commands:")
            for command, desc in jmxfetch.JMX_LIST_COMMANDS.items():
                print("      - %s [OPTIONAL: LIST OF CHECKS]: %s" % (command, desc))
            print("Example: sudo /etc/init.d/monasca-agent jmx list_matching_attributes tomcat jmx solr")
            print("\n")

        else:
            jmx_command = args[1]
            checks_list = args[2:]
            paths = util.Paths()
            confd_path = paths.get_confd_path()
            # Start JMXFetch if needed
            should_run = jmxfetch.JMXFetch.init(confd_path,
                                                config,
                                                15,
                                                jmx_command,
                                                checks_list,
                                                reporter="console")
            if not should_run:
                print("Couldn't find any valid JMX configuration in your conf.d directory: %s" % confd_path)
                print("Have you enabled any JMX checks ?")

    return 0


def run_check(check):

    is_multi_threaded = False
    if isinstance(check, status_checks.ServicesCheck):
        is_multi_threaded = True
    print("#" * 80)
    print("Check name: '{0}'\n".format(check.name))
    check.run()
    # Sleep for a second and then run a second check to capture rate metrics
    time.sleep(1)
    check.run()
    if is_multi_threaded:
        # Sleep for a second to allow async threads to finish
        time.sleep(1)
        check.stop_pool()
    print("Metrics: ")
    check.get_metrics(prettyprint=True)
    print("#" * 80 + "\n\n")

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Try our best to log the error.
        try:
            log.exception("Uncaught error running the Agent")
        except Exception:  # nosec
            pass
        raise
