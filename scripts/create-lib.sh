#!/bin/bash
NAME=$1
echo $NAME


lerna create $NAME 'libs' --private true --yes

# adjust package.json
# create index.ts
