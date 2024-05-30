#!/bin/bash

MAIN_SCRIPT="$(dirname "$0")/main.py"

pkill -f $MAIN_SCRIPT

sleep 5

nohup python3 $MAIN_SCRIPT > "$(dirname "$0")/logs/chatbot.log" 2>&1 &
