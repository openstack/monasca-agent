from fnmatch import fnmatch
from os import stat
from os import walk
from os.path import abspath
from os.path import exists
from os.path import join
import time

from monasca_agent.collector.checks import AgentCheck


class DirectoryCheck(AgentCheck):

    """This check is for monitoring and reporting metrics on the files for a provided directory

    WARNING: the user/group that dd-agent runs as must have access to stat the files in the desired directory

    Config options:
        "directory" - string, the directory to gather stats for. required
        "name" - string, the name to use when tagging the metrics. defaults to the "directory"
        "pattern" - string, the `fnmatch` pattern to use when reading the "directory"'s files. default "*"
        "recursive" - boolean, when true the stats will recurse into directories. default False
    """

    def check(self, instance):
        if "directory" not in instance:
            raise Exception('DirectoryCheck: missing "directory" in config')

        directory = instance["directory"]
        abs_directory = abspath(directory)
        name = instance.get("name") or directory
        pattern = instance.get("pattern") or "*"
        recursive = instance.get("recursive") or False

        if not exists(abs_directory):
            raise Exception("DirectoryCheck: the directory (%s) does not exist" % abs_directory)

        dimensions = self._set_dimensions({"name": name}, instance)
        self._get_stats(abs_directory, name, pattern, recursive, dimensions)

    def _get_stats(self, directory, name, pattern, recursive, dimensions):
        directory_bytes = 0
        directory_files = 0
        for root, dirs, files in walk(directory):
            for filename in files:
                filename = join(root, filename)
                # check if it passes our filter
                if not fnmatch(filename, pattern):
                    continue
                try:
                    file_stat = stat(filename)

                except OSError as ose:
                    self.warning("DirectoryCheck: could not stat file %s - %s" % (filename, ose))
                else:
                    directory_files += 1
                    directory_bytes += file_stat.st_size
                    # file specific metrics
                    self.histogram(
                        "system.disk.directory.file.bytes",
                        file_stat.st_size,
                        dimensions=dimensions)
                    self.histogram(
                        "system.disk.directory.file.modified_sec_ago",
                        time.time() -
                        file_stat.st_mtime,
                        dimensions=dimensions)
                    self.histogram(
                        "system.disk.directory.file.created_sec_ago",
                        time.time() -
                        file_stat.st_ctime,
                        dimensions=dimensions)

            # os.walk gives us all sub-directories and their files
            # if we do not want to do this recursively and just want
            # the top level directory we gave it, then break
            if not recursive:
                break

        # number of files
        self.gauge("system.disk.directory.files", directory_files, dimensions=dimensions)
        # total file size
        self.gauge("system.disk.directory.bytes", directory_bytes, dimensions=dimensions)
