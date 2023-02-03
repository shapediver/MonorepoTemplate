#!/usr/bin/env bash

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Executes the Python command with the given arguments.
# Tries to run `python3`, with fallback to `python`.
# Stops the script when no Python command was found.
function exec_python() {
  if command -v python3 &>/dev/null; then
    python3 "$@"
  elif command -v python &>/dev/null; then
    python "$@"
  else
    echo "Error: No executable for Python 3 found." >&2
    exit 1
  fi
}

# Check active Python version.
# Stops the script when the version of the Python command is invalid.
function check_python_version() {
  # We try to use the same Python version (LTS) for all TypeScript ShapeDiver projects.
  local target_python_version="3.9"

  if ! exec_python -V 2>&1 | grep -q "^Python $(echo "${target_python_version}" | sed -r 's/\.+/\\./g')\."; then
    echo "Invalid Python version: Detected version $(python -V) but requires ${target_python_version}.x." >&2
    exit 1
  fi
}

# Activates the Python virtual environment in the current shell.
# Tries to activate the venv first for Unix & Mac, with fallback to Windows.
# Stops the script when the virtual environment could not be activated.
function activate_python_venv() {
  if pushd "${__dir}/../.venv/bin/" &>/dev/null || pushd "${__dir}/../.venv/Scripts/" &>/dev/null; then
    source "./activate"
  else
    echo "Could not activate Python virtual environment: Run 'npm run init' to setup Python." >&2
    exit 1
  fi
}

# Tries to run a script that is located in `./custom/` and that has the same name as the calling
# script. If a custom script was found, the shell is stopped with the script's exit status.
# Otherwise, nothing happens.
function try_run_custom_script() {
  custom_script="${__dir}/custom/${0##*/}"

  if [[ -f "${custom_script}" ]]; then
    # shellcheck source=/dev/null
    source "${custom_script}" "$@"
    exit "$?"
  fi
}
