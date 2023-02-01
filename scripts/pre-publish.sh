#!/usr/bin/env bash
# This script is called by the Publish command of the Python maintain CLI tool.
#
# The CLI tool calls this script before a component is published. Use this script to run prepare
# individual components.
#
# WARNING: A non-zero exit status prevents the publishing process to be continued.
#
# The following stringified arguments are available:
#   [1] dry-run {boolean}:
#       Is `True` when the user don't want to actually publish anything. Instead this script should
#       only report what would have happened for testing and development purposes.
#       Otherwise, this property is set to `False`.
#   [2] no-git {boolean}:
#       Is `True` when the user don't want to actually create any git commits. Instead, changed
#       files should be keeps in the index.
#       Otherwise, this property is set to `False`.
#   [3] name {string}:
#       The name of the the component that is about to get published.
#   [4] version {string}:
#       The new-version of the the component that is about to get published.

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Try to run a custom script of the same name.
# When no script was found, continue and run the default behaviour instead.
try_run_custom_script "$@"

# Show debug output when the publish command is executed in dry-run mode.
if [[ "$1" == "True" ]] ; then
  echo "Running script '$0' with the following arguments:"
  echo "[1] dry-run = $1"
  echo "[2] no-git = $2"
  echo "[3] name = $3"
  echo "[4] version = $4"
fi

npm run build
