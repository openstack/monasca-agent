# (C) Copyright 2015,2017 Hewlett Packard Enterprise Development LP


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


class MissingEnvironmentVariables(Exception):
    pass


class KubernetesAPIConnectionError(Exception):
    pass
