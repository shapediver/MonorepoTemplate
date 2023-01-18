#!/usr/bin/env bash
# This script is called by the Publish command of the Python maintain CLI tool.
#
# The CLI tool calls this script after a component has been published. Use this script to run
# cleanup steps for individual components.
#
# WARNING: A non-zero exit status prevents the publishing process to be continued.
#
# The following stringified arguments are available:
#   [1] dry-run {boolean}:
#       Is `True` when the CLI process is running with the `--dry-run` flag; otherwise `False`.
#   [2] name {string}:
#       The name of the the component that is about to get published.
#   [3] version {string}:
#       The new-version of the the component that is about to get published.

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Show debug output when the publish command is executed in dry-run mode.
if [[ "$1" == "True" ]] ; then
  echo "Running script '$0' with the following arguments:"
  echo "[1] dry-run = $1"
  echo "[2] name = $2"
  echo "[3] version = $3"
fi

# Try to run a custom script of the same name.
# When no script was found, continue and run the default behaviour instead.
try_run_custom_script "$@"

# There is no default behaviour for the pre-publish lifecycle!
