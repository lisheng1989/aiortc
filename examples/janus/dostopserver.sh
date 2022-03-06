#!/bin/bash
ps -ef | grep newserver.py | grep -v "grep" | awk '{print $2}' | xargs sudo kill -9 >/dev/null 2>&1
