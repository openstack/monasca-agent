# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

import logging
import os
import psutil
import re

log = logging.getLogger(__name__)

import monasca_agent.collector.checks as checks


class Disk(checks.AgentCheck):

    def __init__(self, name, init_config, agent_config):
        self._partition_error = set()

        super(Disk, self).__init__(name, init_config, agent_config)

    def _log_once_per_day(self, message):
        if message in self._partition_error:
            return
        self._partition_error.add(message)
        log.exception(message)

    def check(self, instance):
        """Capture disk stats

        """
        dimensions = self._set_dimensions(None, instance)
        rollup_dimensions = dimensions.copy()

        if instance is not None:
            use_mount = instance.get("use_mount", True)
            send_io_stats = instance.get("send_io_stats", True)
            send_rollup_stats = instance.get("send_rollup_stats", False)
            # If we filter devices, get the list.
            device_blacklist_re = self._get_re_exclusions(instance)
            fs_types_to_ignore = self._get_fs_exclusions(instance)
        else:
            use_mount = True
            send_io_stats = True
            send_rollup_stats = False
            device_blacklist_re = None
            fs_types_to_ignore = set()

        partitions = psutil.disk_partitions(all=True)
        if send_io_stats:
            disk_stats = psutil.disk_io_counters(perdisk=True)
        disk_count = 0
        total_capacity = 0
        total_used = 0
        for partition in partitions:
            if partition.fstype not in fs_types_to_ignore \
                and (not device_blacklist_re
                     or not device_blacklist_re.match(partition.device)):
                    try:
                        device_name = self._get_device_name(partition.device)
                        disk_usage = psutil.disk_usage(partition.mountpoint)
                        total_capacity += disk_usage.total
                        total_used += disk_usage.used
                        st = os.statvfs(partition.mountpoint)
                    except Exception as ex:
                        exception_name = ex.__class__.__name__
                        self._log_once_per_day('Unable to access partition {} '
                                               'with error: {}'.format(partition,
                                                                       exception_name))
                        continue

                    if use_mount:
                        dimensions.update({'mount_point': partition.mountpoint})
                    self.gauge("disk.space_used_perc",
                               disk_usage.percent,
                               device_name=device_name,
                               dimensions=dimensions)
                    disk_count += 1
                    if st.f_files > 0:
                        self.gauge("disk.inode_used_perc",
                                   round((float(st.f_files - st.f_ffree) / st.f_files) * 100, 2),
                                   device_name=device_name,
                                   dimensions=dimensions)
                        disk_count += 1

                    log.debug('Collected {0} disk usage metrics for partition {1}'.format(disk_count, partition.mountpoint))
                    disk_count = 0
                    if send_io_stats:
                        try:
                            stats = disk_stats[device_name]
                            self.rate("io.read_req_sec", round(float(stats.read_count), 2), device_name=device_name, dimensions=dimensions)
                            self.rate("io.write_req_sec", round(float(stats.write_count), 2), device_name=device_name, dimensions=dimensions)
                            self.rate("io.read_kbytes_sec", round(float(stats.read_bytes / 1024), 2), device_name=device_name, dimensions=dimensions)
                            self.rate("io.write_kbytes_sec", round(float(stats.write_bytes / 1024), 2), device_name=device_name, dimensions=dimensions)
                            self.rate("io.read_time_sec", round(float(stats.read_time / 1000), 2), device_name=device_name, dimensions=dimensions)
                            self.rate("io.write_time_sec", round(float(stats.write_time / 1000), 2), device_name=device_name, dimensions=dimensions)

                            log.debug('Collected 6 disk I/O metrics for partition {0}'.format(partition.mountpoint))
                        except KeyError:
                            log.debug('No Disk I/O metrics available for {0}...Skipping'.format(device_name))

        if send_rollup_stats:
            self.gauge("disk.total_space_mb",
                       total_capacity / 1048576,
                       dimensions=rollup_dimensions)
            self.gauge("disk.total_used_space_mb",
                       total_used / 1048576,
                       dimensions=rollup_dimensions)
            log.debug('Collected 2 rolled-up disk usage metrics')

    def _get_re_exclusions(self, instance):
        """Parse device blacklist regular expression"""
        filter = None
        try:
            filter_device_re = instance.get('device_blacklist_re', None)
            if filter_device_re:
                filter = re.compile(filter_device_re)
        except re.error:
            log.error('Error processing regular expression {0}'.format(filter_device_re))

        return filter

    def _get_fs_exclusions(self, instance):
        """parse comma separated file system types to ignore list"""
        file_system_list = set()

        # automatically ignore filesystems not backed by a device
        try:
            for nodevfs in filter(lambda x: x.startswith('nodev\t'), file('/proc/filesystems')):
                file_system_list.add(nodevfs.partition('\t')[2].strip())
        except IOError:
            log.debug('Failed reading /proc/filesystems')

        try:
            file_systems = instance.get('ignore_filesystem_types', None)
            if file_systems:
                # Parse file system types
                file_system_list.update(x.strip() for x in file_systems.split(','))
        except ValueError:
            log.info("Unable to process ignore_filesystem_types.")

        return file_system_list

    def _get_device_name(self, device):
        start = device.rfind("/")
        if start > -1:
            device_name = device[start + 1:]
        else:
            device_name = device

        return device_name
