#!/usr/bin/env bash
__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Activate virtual environment
activate_python_venv

# Check NPM and Python versions
npm run check-npm-version
check_python_version

# Run Python command
exec_python "${__dir}/repomaintain/cli.py" "$@"

# Deactivate virtual environment
deactivate
