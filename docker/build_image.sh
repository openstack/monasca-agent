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

# Dummy script for building both images for monasca-agent: collector and
# forwarder. It will relay all arguments to every image build script.

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
cd "$(dirname "$REAL_PATH")/../docker/"

./collector/build_image.sh "$@"

printf "\n\n\n"

./forwarder/build_image.sh "$@"

printf "\n\n\n"

./statsd/build_image.sh "$@"
