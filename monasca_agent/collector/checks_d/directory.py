# (C) Copyright 2015-2016 Hewlett Packard Enterprise Development Company LP

from monasca_agent.collector.checks import AgentCheck
from os.path import abspath
from os.path import exists
from os.path import join

from os import access
from os import stat
from os import walk

from os import X_OK

import logging

log = logging.getLogger(__name__)
missing_dir_instance = set()
non_exist_dir = set()
no_access_sub_dir = set()
no_stat_file = set()


class DirectoryCheck(AgentCheck):

    """This check is for monitoring and reporting metrics on the provided directory

    WARNING: the user/group that mon-agent runs as must have access to stat
    the files in the desired directory

    Config options:
        "directory" - string, the directory to gather stats for. required
    """

    def check(self, instance):
        global missing_dir_instance
        global non_exist_dir
        if "directory" not in instance:
            if instance['dimensions']['service'] not in missing_dir_instance:
                missing_dir_instance.add(instance['dimensions']['service'])
                log.error('DirectoryCheck: missing "directory" in config')
        else:
            directory = instance["directory"]
            abs_directory = abspath(directory)
            if not exists(abs_directory) and abs_directory not in non_exist_dir:
                non_exist_dir.add(abs_directory)
                log.error("DirectoryCheck: the directory (%s) does not exist" % abs_directory)

            dimensions = self._set_dimensions({"path": directory}, instance)
            self._get_stats(abs_directory, dimensions)

    def _get_stats(self, directory_name, dimensions):
        global no_access_sub_dir
        global no_stat_file
        directory_bytes = 0
        directory_files = 0
        for root, dirs, files in walk(directory_name):
            for directory in dirs:
                directory_root = join(root, directory)
                if not access(directory_root, X_OK) and directory_root not in no_access_sub_dir:
                    no_access_sub_dir.add(directory_root)
                    log.warn("DirectoryCheck: could not access sub directory "
                             "{}".format(directory_root))
            for filename in files:
                filename = join(root, filename)
                try:
                    file_stat = stat(filename)
                except OSError as ose:
                    if filename not in no_stat_file:
                        no_stat_file.add(filename)
                        log.warn("DirectoryCheck: could not stat file %s - "
                                 "%s" % (filename, ose))
                else:
                    directory_files += 1
                    directory_bytes += file_stat.st_size

        # number of files
        self.gauge("directory.files_count", directory_files,
                   dimensions=dimensions)
        # total file size
        self.gauge("directory.size_bytes", directory_bytes,
                   dimensions=dimensions)
        log.debug("DirectoryCheck: Directory {0} size {1} bytes with {2} "
                  "files in it.".format(directory_name, directory_bytes,
                                        directory_files))
