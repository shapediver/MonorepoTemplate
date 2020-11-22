#!/bin/bash
NAME=$1
echo $NAME


lerna create $NAME 'packages' --private true --yes

# adjust package.json
# create index.ts
