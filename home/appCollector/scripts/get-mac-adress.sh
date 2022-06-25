#!/bin/bash
sudo timeout -s SIGINT 10s hcitool lescan | grep "$1" | awk '{ print $1 }' | sort | uniq -d
