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


class DirectoryCheck(AgentCheck):

    """This check is for monitoring and reporting metrics on the provided directory

    WARNING: the user/group that mon-agent runs as must have access to stat
    the files in the desired directory

    Config options:
        "directory" - string, the directory to gather stats for. required
    """

    def check(self, instance):
        if "directory" not in instance:
            error_message = 'DirectoryCheck: missing "directory" in config'
            log.error(error_message)
            raise Exception(error_message)

        directory = instance["directory"]
        abs_directory = abspath(directory)

        if not exists(abs_directory):
            error_message = "DirectoryCheck: the directory (%s) does not " \
                            "exist" % abs_directory
            log.error(error_message)
            raise Exception(error_message)

        dimensions = self._set_dimensions({"path": directory}, instance)
        self._get_stats(abs_directory, dimensions)

    def _get_stats(self, directory_name, dimensions):
        directory_bytes = 0
        directory_files = 0
        for root, dirs, files in walk(directory_name):
            for directory in dirs:
                directory_root = join(root, directory)
                if not access(directory_root, X_OK):
                    log.warn("DirectoryCheck: could not access directory {}".
                             format(directory_root))
            for filename in files:
                filename = join(root, filename)
                try:
                    file_stat = stat(filename)
                except OSError as ose:
                    log.warn("DirectoryCheck: could not stat file %s - %s" %
                             (filename, ose))
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
