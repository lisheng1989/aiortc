#!/bin/bash
if [ $# != 1 ];
then
echo "USAGE:$0 roomid"
echo "e.g.:$0 1235"
exit 1;
fi
echo $1
sh dostop.sh >/dev/null 2>&1 &
nohup python3 janus.py --room $1 https://ws.ychzp.top/janus >/dev/null 2>&1 &

