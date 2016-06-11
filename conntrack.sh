#!/bin/bash

ctmax=0

while [ 1 ]; do
	ct=$(conntrack -C)

	if [ $ct -gt $ctmax ]; then
		ctmax=$ct
	fi

	echo -en "\rConnections tracking: $ct (Max: $ctmax) "
	
	sleep 1
done
