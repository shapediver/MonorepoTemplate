#!/usr/bin/env bash
set -o errexit
set -o pipefail
set -o nounset

# We try to use the same Node.js (LTS) and NPM versions for all TypeScript ShapeDiver projects.
target_node_version="v16"
target_npm_version="8"
target_pnpm_version="8"

node_version=$(node -v | cut -d. -f1)
npm_version=$(npm -v | cut -d. -f1)
pnpm_version=$(pnpm -v | cut -d. -f1)

# Check Node.js
if [ "${node_version}" != "${target_node_version}" ]; then
  echo "Invalid Node.js version: Detected major version ${node_version} but requires ${target_node_version}." >&2
  exit 1
fi

# Check NPM
if [ "${npm_version}" != "${target_npm_version}" ]; then
  echo "Invalid NPM version: Detected major version ${npm_version} but requires version ${target_npm_version}." >&2
  exit 1
fi

# Check pNPM
if [ "${pnpm_version}" != "${target_pnpm_version}" ]; then
  echo "Invalid pNPM version: Detected major version ${pnpm_version} but requires version ${target_pnpm_version}." >&2
  exit 1
fi

