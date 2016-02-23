# (C) Copyright 2016 Hewlett Packard Enterprise Development Company LP

from os.path import abspath
from os.path import exists
from os.path import isfile
from os.path import join

from os import listdir
from os import stat
from os import walk

import logging
import monasca_agent.collector.checks as checks

log = logging.getLogger(__name__)


class FileSize(checks.AgentCheck):

    """This check is for monitoring and reporting metrics on the size of
    files for a provided directory

    Config options:
        "directory_name" - string, directory of the file (required)
        "file_names" - list of strings, file names under directory_name to
                       gather stats for (required)
        "recursive" - boolean, when true and file_name is set to '*' will
                      recursively grab files under the given directory to
                      gather stats on.
    """
    def __init__(self, name, init_config, agent_config, instances=None):
        super(FileSize, self).__init__(name, init_config, agent_config,
                                       instances)

    def check(self, instance):
        if "directory_name" not in instance:
            raise Exception('FileSize Check: missing "directory_name" in '
                            'config')
        if "file_names" not in instance:
            raise Exception('FileSize Check: missing "file_names" in config')
        recursive = instance.get("recursive") or False
        directory_name = instance["directory_name"]
        abs_directory = abspath(directory_name)
        if exists(abs_directory):
            if instance["file_names"] != ['*']:
                file_names = instance["file_names"]
                self._get_stats(abs_directory, file_names, instance)
            else:
                if recursive:
                    for root, dirs, files in walk(abs_directory):
                        self._get_stats(root, files, instance)
                else:
                    files = [file_name for file_name in listdir(abs_directory)
                             if isfile(join(abs_directory, file_name))]
                    self._get_stats(abs_directory, files, instance)
        else:
            log.error('FileSize Check: directory {0} does not exist'.
                      format(abs_directory))

    def _get_stats(self, directory_name, files, instance):
        num_files = 0
        for file_name in files:
            abs_dir_name = abspath(join(directory_name, file_name))
            if isfile(abs_dir_name):
                dimensions = self._set_dimensions({
                    "file_name": file_name,
                    "directory_name": directory_name}, instance)
                got_stats = False
                file_abs_path = join(directory_name, file_name)
                try:
                    file_stat = stat(file_abs_path)
                except OSError as ose:
                    log.warn("FileSize Check: could not stat file %s - %s" % (
                        file_abs_path, ose))
                else:
                    file_bytes = file_stat.st_size
                    self.gauge("file.size_bytes", file_bytes,
                               dimensions=dimensions)
                    got_stats = True
                if got_stats:
                    num_files += 1
            else:
                log.error('FileSize Check: file {0} does not exist'.
                          format(abs_dir_name))
        log.debug('Collected {0} file_size metrics from {1}'.
                  format(num_files, directory_name))
