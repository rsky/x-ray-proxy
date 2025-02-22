#/usr/bin/env bash

find sql -name \*.sql -print -exec sql-formatter {} -o {} \;
