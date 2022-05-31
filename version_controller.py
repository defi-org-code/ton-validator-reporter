import os
from pathlib import Path
import sys
import time
from datetime import datetime
import logging
import json
from urllib import request

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *


class VersionController(object):
	VERSION_DESCRIPTOR = ""

	SECONDS_IN_YEAR = 365 * 24 * 3600
	SLEEP_INTERVAL = 60

	def __init__(self):
		super(VersionController, self).__init__()

	def run(self):

		while True:

			try:
				with request.urlopen(self.VERSION_DESCRIPTOR) as url:
					data = json.loads(url.read().decode())
					print(data)

			except Exception as e:
				print(e)
				# self.log.info('unexpected error: ', e)
				# self.log.info(res)

			sleep_sec = self.SLEEP_INTERVAL - time.time() % self.SLEEP_INTERVAL
			# self.log.info(f'sleep for {round(sleep_sec)} seconds')
			time.sleep(sleep_sec)


if __name__ == '__main__':
	vc = VersionController()
	vc.run()
