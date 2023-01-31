#!/usr/bin/env bash

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Try to run a custom script of the same name.
# When no script was found, continue and run the default behaviour instead.
try_run_custom_script "$@"

rm -rf ./dist
tsc -b
