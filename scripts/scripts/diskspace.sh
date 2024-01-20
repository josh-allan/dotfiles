#!/usr/bin/bash

du -ah $1 | grep -v "/$" | sort -rh | less
