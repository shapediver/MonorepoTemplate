#!/usr/bin/env bash
# This script is called by the Publish command of the Python maintain CLI tool.
#
# The CLI tool calls this script after all components have been published and the commit message has
# been created. Use this script to run cleanup steps that should be done at a repository level.
#
# A non-zero exit status prevents the publishing process to be continued.
#
# The following stringified arguments are available:
#   [1] dry-run {boolean}:
#       Is `True` when the user don't want to actually publish anything. Instead this script should
#       only report what would have happened for testing and development purposes.
#       Otherwise, this property is set to `False`.
#   [2] components {object[]}:
#       Information about all components that have been published, in the format
#        ```
#        [ {
#          "component": {
#            "name": string,
#            "version": string,
#            "location": string,
#            "private": boolean
#          },
#          "new_version": string
#        } ]
#        ```

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Show debug output when the publish command is executed in dry-run mode.
if [[ "$1" == "True" ]] ; then
  echo "Running script '$0' with the following arguments:"
  echo "[1] dry-run = $1"
  echo "[2] components = $(echo "$2" | npx json)"
fi

# Try to run a custom script of the same name.
# When no script was found, continue and run the default behaviour instead.
try_run_custom_script "$@"

# There is no default behaviour for the pre-publish lifecycle!
