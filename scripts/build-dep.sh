#!/usr/bin/env bash
rm -rf ./dist
lerna run build --stream --scope=$npm_package_name --include-dependencies
