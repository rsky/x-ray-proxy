#/usr/bin/env bash

find sql -name \*.sql -print -exec sql-formatter -l sqlite {} -o {} \;
