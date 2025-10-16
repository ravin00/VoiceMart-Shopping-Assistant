#!/bin/bash

# First, make sure we're at the repository root
cd "$(git rev-parse --show-toplevel)"

git filter-branch --force --env-filter '
if [ "$GIT_AUTHOR_NAME" = "ravin00" ] || [ "$GIT_COMMITTER_NAME" = "ravin00" ]
then
    export GIT_AUTHOR_NAME="SithikaRavindith"
    export GIT_AUTHOR_EMAIL="it22896186@my.sliit.lk"
    export GIT_COMMITTER_NAME="SithikaRavindith"
    export GIT_COMMITTER_EMAIL="it22896186@my.sliit.lk"
fi
' --tag-name-filter cat -- --all