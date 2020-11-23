#!/bin/bash
VERSION=$(npm -v)
if [ $VERSION = '6.14.5' ]
then
    exit 0
else
    echo 'You need to switch to a different version (6.14.5, node 14.5.0) of npm to continue.'
    exit 1
fi