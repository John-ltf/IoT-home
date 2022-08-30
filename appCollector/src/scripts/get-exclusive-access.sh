#!/bin/bash
#set -xv

#################################################
# GETTING EXCLUSIVE LOCK                        #
#################################################
exec {lock_fd}>/var/lock/bluetooth.lock || exit 1
flock -x "$lock_fd" || { echo "ERROR: flock() failed." >&2; exit 1; }
echo "Getting EXCLUSIVE lock..."


#################################################
# WAIT FOR SIGNAL                               #
#################################################
trap 'quit=1' USR1

quit=0
while [ "$quit" -ne 1 ]; do
    #printf 'Do "kill -USR1 %d" to exit this loop after the sleep\n' "$$"
    sleep 1
done

#################################################
# REMOVING EXCLUSIVE LOCK                       #
#################################################
#REMOVE LOCK FILE
echo "Removing EXCLUSIVE lock..."
flock -u "$lock_fd"
