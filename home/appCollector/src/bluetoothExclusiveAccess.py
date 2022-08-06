import logging
import os
import sys
import fcntl
import errno
import time
from os.path import exists

class bluetoothExclusiveAccess:
    lock_file = "/var/lock/bluetooth.lock"

    def __init__(self, appId: str):
        self.appId = appId
        if not exists(self.lock_file):
            open(self.lock_file,'a+')

    def __writeContent(self, content: str):
        fd = open(bluetoothExclusiveAccess.lock_file, 'w+')
        fd.write(content)
        fd.close()

    def acquire(self):
        try:
            self.lock_file_fd = os.open(bluetoothExclusiveAccess.lock_file, os.O_RDONLY)
            fcntl.flock(self.lock_file_fd, fcntl.LOCK_EX)
            logging.debug(f"Exclusive Lock {self.appId}")
            self.__writeContent(self.appId)
        except OSError as e:
            logging.error(f"Could not lock file: {e.errno} {e.strerror}", file=sys.stderr)

    def release(self):
        logging.debug(f"Release Lock {self.appId}")
        fcntl.flock(self.lock_file_fd, fcntl.LOCK_UN)
        os.close(self.lock_file_fd)
        self.__writeContent("")

