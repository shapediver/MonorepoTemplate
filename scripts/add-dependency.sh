#!/usr/bin/env bash
# Validate input
[ $# -lt 1 ] && echo "Error: Specify the dependency name." >&2 && exit 1

dependency=$1
component=${2/@shapediver\//} # Remove '@shapediver/' prefix from component

if [ -z "${component}" ]; then
  lerna add "${dependency}"
else
  lerna add "${dependency}" "packages/${component}"
  lerna add "${dependency}" "libs/${component}"
fi
