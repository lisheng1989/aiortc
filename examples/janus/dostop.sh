#!/bin/bash
ps -ef | grep janus.py | grep -v grep | cut -c 9-15 | xargs kill -s 9
