#!/usr/bin/env bash
# Validate input
[ $# -lt 1 ] && echo "Error: Specify the dev-dependency name." >&2 && exit 1

dependency=$1
component=${2/@shapediver\//} # Remove '@shapediver/' prefix from component

if [ -z "${component}" ]; then
  lerna add "${dependency}" --dev
else
  lerna add "${dependency}" "packages/${component}" --dev
  lerna add "${dependency}" "libs/${component}" --dev
fi
