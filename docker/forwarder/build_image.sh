#!/bin/bash

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

# TODO(Dobroslaw): move this script to monasca-common/docker folder
# and leave here small script to download it and execute using env variables
# to minimize code duplication.

set -x  # Print each script step.
set -eo pipefail  # Exit the script if any statement returns error.

# This script is used for building Docker image with proper labels
# and proper version of monasca-common.
#
# Example usage:
#   $ ./build_image.sh <repository_version> <upper_constains_branch> <common_version>
#
# Everything after `./build_image.sh` is optional and by default configured
# to get versions from `Dockerfile`.
#
# To build from master branch (default):
#   $ ./build_image.sh
# To build specific version run this script in the following way:
#   $ ./build_image.sh stable/queens
# Building from specific commit:
#   $ ./build_image.sh cb7f226
# When building from a tag monasca-common will be used in version available
# in upper constraint file:
#   $ ./build_image.sh 2.5.0
# To build image from Gerrit patch sets that is targeting branch stable/queens:
#   $ ./build_image.sh refs/changes/51/558751/1 stable/queens
#
# If you want to build image with custom monasca-common version you need
# to provide it as in the following example:
#   $ ./build_image.sh master master refs/changes/19/595719/3

# Go to folder with Docker files.
REAL_PATH=$(python3 -c "import os,sys; print(os.path.realpath('$0'))")
cd "$(dirname "$REAL_PATH")/../forwarder/"

[ -z "$DOCKER_IMAGE" ] && \
    DOCKER_IMAGE=$(\grep DOCKER_IMAGE Dockerfile | cut -f2 -d"=")

: "${REPO_VERSION:=$1}"
[ -z "$REPO_VERSION" ] && \
    REPO_VERSION=$(\grep REPO_VERSION Dockerfile | cut -f2 -d"=")
# Let's stick to more readable version and disable SC2001 here.
# shellcheck disable=SC2001
REPO_VERSION_CLEAN=$(echo "$REPO_VERSION" | sed 's|/|-|g')

[ -z "$APP_REPO" ] && APP_REPO=$(\grep APP_REPO Dockerfile | cut -f2 -d"=")
GITHUB_REPO=$(echo "$APP_REPO" | sed 's/review.opendev.org/github.com/' | \
              sed 's/ssh:/https:/')

if [ -z "$CONSTRAINTS_FILE" ]; then
    CONSTRAINTS_FILE=$(\grep CONSTRAINTS_FILE Dockerfile | cut -f2 -d"=") || true
    : "${CONSTRAINTS_FILE:=https://opendev.org/openstack/requirements/raw/branch/master/upper-constraints.txt}"
fi

: "${CONSTRAINTS_BRANCH:=$2}"
[ -z "$CONSTRAINTS_BRANCH" ] && \
    CONSTRAINTS_BRANCH=$(\grep CONSTRAINTS_BRANCH Dockerfile | cut -f2 -d"=")

# When using stable version of repository use same stable constraints file.
case "$REPO_VERSION" in
    *stable*)
        CONSTRAINTS_BRANCH_CLEAN="$REPO_VERSION"
        CONSTRAINTS_FILE=${CONSTRAINTS_FILE/master/$CONSTRAINTS_BRANCH_CLEAN}
        # Get monasca-common version from stable upper constraints file.
        CONSTRAINTS_TMP_FILE=$(mktemp)
        wget --output-document "$CONSTRAINTS_TMP_FILE" \
            $CONSTRAINTS_FILE
        UPPER_COMMON=$(\grep 'monasca-common' "$CONSTRAINTS_TMP_FILE")
        # Get only version part from monasca-common.
        UPPER_COMMON_VERSION="${UPPER_COMMON##*===}"
        rm -rf "$CONSTRAINTS_TMP_FILE"
    ;;
    *)
        CONSTRAINTS_BRANCH_CLEAN="$CONSTRAINTS_BRANCH"
    ;;
esac

# Monasca-common variables.
if [ -z "$COMMON_REPO" ]; then
    COMMON_REPO=$(\grep COMMON_REPO Dockerfile | cut -f2 -d"=") || true
    : "${COMMON_REPO:=https://review.opendev.org/openstack/monasca-common}"
fi
: "${COMMON_VERSION:=$3}"
if [ -z "$COMMON_VERSION" ]; then
    COMMON_VERSION=$(\grep COMMON_VERSION Dockerfile | cut -f2 -d"=") || true
    if [ "$UPPER_COMMON_VERSION" ]; then
        # Common from upper constraints file.
        COMMON_VERSION="$UPPER_COMMON_VERSION"
    fi
fi

# Clone project to temporary directory for getting proper commit number from
# branches and tags. We need this for setting proper image labels.
# Docker does not allow to get any data from inside of system when building
# image.
TMP_DIR=$(mktemp -d)
(
    cd "$TMP_DIR"
    # This many steps are needed to support gerrit patch sets.
    git init
    git remote add origin "$APP_REPO"
    git fetch origin "$REPO_VERSION"
    git reset --hard FETCH_HEAD
)
GIT_COMMIT=$(git -C "$TMP_DIR" rev-parse HEAD)
[ -z "${GIT_COMMIT}" ] && echo "No git commit hash found" && exit 1
rm -rf "$TMP_DIR"

# Do the same for monasca-common.
COMMON_TMP_DIR=$(mktemp -d)
(
    cd "$COMMON_TMP_DIR"
    # This many steps are needed to support gerrit patch sets.
    git init
    git remote add origin "$COMMON_REPO"
    git fetch origin "$COMMON_VERSION"
    git reset --hard FETCH_HEAD
)
COMMON_GIT_COMMIT=$(git -C "$COMMON_TMP_DIR" rev-parse HEAD)
[ -z "${COMMON_GIT_COMMIT}" ] && echo "No git commit hash found" && exit 1
rm -rf "$COMMON_TMP_DIR"

CREATION_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

docker build --no-cache \
    --build-arg CREATION_TIME="$CREATION_TIME" \
    --build-arg GITHUB_REPO="$GITHUB_REPO" \
    --build-arg APP_REPO="$APP_REPO" \
    --build-arg REPO_VERSION="$REPO_VERSION" \
    --build-arg GIT_COMMIT="$GIT_COMMIT" \
    --build-arg CONSTRAINTS_FILE="$CONSTRAINTS_FILE" \
    --build-arg COMMON_REPO="$COMMON_REPO" \
    --build-arg COMMON_VERSION="$COMMON_VERSION" \
    --build-arg COMMON_GIT_COMMIT="$COMMON_GIT_COMMIT" \
    --tag "$DOCKER_IMAGE":"$REPO_VERSION_CLEAN" .
