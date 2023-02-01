#!/usr/bin/env bash
# This script is called by the Publish command of the Python maintain CLI tool.
#
# The CLI tool calls this script after the user has selected all Lerna components that should be
# published and their respective new versions, but before any further publishing steps have been
# executed. Use this script to run preparation steps that should be done at a repository level.
#
# A non-zero exit status prevents the publishing process to be continued.
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
#   [3] components {object[]}:
#       Information about all components selected for publishing, in the format
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
#   [4] registries {object[]}:
#       Information about all selected registries that are targeted during publishing, in the format
#        ```
#        [ {
#          "name": "github" | "npm",
#          "url": string
#        } ]
#        ```

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
  echo "[3] components = $(echo "$3" | npx json)"
  echo "[4] registries = $(echo "$4" | npx json)"
fi

# There is no default behaviour for the pre-publish lifecycle!
