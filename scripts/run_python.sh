#!/usr/bin/env bash
# Validates the Python version and activates the virtual environment of this repository before
# running the specified Python script.
#
# Arguments:
#   [0]:  Specifies the Python script to run. This can either be an absolute path, a path relative to
#         the callers working directory, or an identifier. Currently the following identifiers are
#         supported:
#           * [cli|CLI]: Shortcut for `scripts/repomaintain/cli.py`.
#   [1:]: These arguments are passed forward as is to the Python script that is executed.
#
# Usage - Run the CLI tool 'repomaintain':
#   ./scripts/run_python.sh cli sd-global list-pinned
#
# Usage - Run a custom Python script:
#   ./scripts/run_python.sh ./scripts/custom/dummy.py -a 'foo' -b 'bar'

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Validate input
[ $# -lt 1 ] && echo "Error: Specify the Python script to run." >&2 && exit 1

# Activate virtual environment but stay in the callers working directory
pushd "$(pwd)" >/dev/null || exit 1
activate_python_venv
popd >/dev/null || exit 1

# Check NPM and Python versions
npm run check-npm-version
check_python_version

# Map path from identifier if specified
if [ "$1" == 'cli' ] || [ "$1" == "CLI" ]; then
  path="${__dir}/repomaintain/cli.py"
else
  path="$1"
fi

# Run Python command
exec_python "${path}" "${@:2}" || exit $?

# Deactivate virtual environment
deactivate
