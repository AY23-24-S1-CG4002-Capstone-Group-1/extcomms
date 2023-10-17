#!/bin/bash

input="commands.txt"

while read -r line
do 
	echo "$line"
	sleep 1.2
done < "$input" | python viz_commands.py

/bin/bash



