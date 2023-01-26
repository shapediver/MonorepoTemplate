#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${__dir}/utils.sh"

# Check Python
check_python_version

# Remove old versions file
rm "${__dir}/../.python-version" 2>/dev/null || :

# Create a new Python virtual environment for this application
python -m venv "${__dir}/../.venv"

# Activate virtual environment
activate_python_venv

# Install all dependencies needed for Monorepo scripts
if [ -f "${__dir}/../requirements.txt" ]; then
  pip install -r "${__dir}/../requirements.txt"
else
  echo "Could not install Python dependencies: File requirements.txt was not found."
  exit 1
fi

# Install all dependencies needed for custom Python scripts
if [ -f "${__dir}/custom/requirements.txt" ]; then
  pip install -r "${__dir}/custom/requirements.txt"
fi
