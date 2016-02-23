# (C) Copyright 2015 Hewlett Packard Enterprise Development Company LP


class Infinity(Exception):
    pass


class UnknownValue(Exception):
    pass


class CheckException(Exception):
    pass


class NaN(CheckException):
    pass


class PathNotFound(Exception):
    pass
