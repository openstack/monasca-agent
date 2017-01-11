#!/usr/bin/env bash

# Client constraint file contains this client version pin that is in conflict
# with installing the client from source. We should remove the version pin in
# the constraints file before applying it for from-source installation.

CONSTRAINTS_FILE="$1"
shift 1

set -e

# NOTE(tonyb): Place this in the tox enviroment's log dir so it will get
# published to logs.openstack.org for easy debugging.
localfile="$VIRTUAL_ENV/log/upper-constraints.txt"

if [[ "$CONSTRAINTS_FILE" != http* ]]; then
    CONSTRAINTS_FILE="file://$CONSTRAINTS_FILE"
fi
# NOTE(tonyb): need to add curl to bindep.txt if the project supports bindep
curl "$CONSTRAINTS_FILE" --insecure --progress-bar --output "$localfile"

pip install -c"$localfile" openstack-requirements

# This is the main purpose of the script: Allow local installation of
# the current repo. It is listed in constraints file and thus any
# install will be constrained and we need to unconstrain it.

# NOTE(dmllr): temporary local uncaping of psutil in upper-constraints
# if it is still 1.x. Remove me when https://review.openstack.org/#/c/333717/
# merges
edit-constraints "$localfile" -- "$CLIENT_NAME" psutil===3.0.1

pip install -c"$localfile" -U "$@"
exit $?
