import os
import time
import json
from urllib import request
from packaging import version
from subprocess import call
import logging


class VersionController(object):
	VERSION_DESCRIPTOR = 'https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/version.txt'
	INSTALLER_DESCRIPTOR = 'https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/installer.sh'

	REPORTER_DIR = f'/var/reporter'
	REPORTER_PARAMS_FILE = f'{REPORTER_DIR}/params.json'

	SECONDS_IN_YEAR = 365 * 24 * 3600
	SLEEP_INTERVAL = 5 * 60
	version = None

	LOG_FILENAME = f'/var/log/reporter/version_controller.log'

	def __init__(self):
		super(VersionController, self).__init__()

		logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)s - %(message)s', datefmt='%m-%d-%Y %H:%M:%S.%f', filename=self.LOG_FILENAME, level=logging.INFO)
		self.log = logging

		self.version = self.get_version()

	def get_version(self):

		self.log.info(f'reading version file from {self.REPORTER_PARAMS_FILE}')

		validator_params = {}
		if os.path.isfile(self.REPORTER_PARAMS_FILE):
			with open(self.REPORTER_PARAMS_FILE, 'r') as f:
				validator_params = json.load(f)

		if 'version' not in validator_params:
			validator_params['version'] = '0.0.0'
			self.log.info(f'updating {self.REPORTER_PARAMS_FILE} with version {validator_params["version"]}')
			with open(self.REPORTER_PARAMS_FILE, 'w') as f:
				json.dump(validator_params, f)

		self.log.info(f'current version is {validator_params["version"]}')
		return version.Version(validator_params['version'])

	def run(self):

		while True:

			try:
				with request.urlopen(self.VERSION_DESCRIPTOR) as url:
					data = url.read().decode().strip()
					curr_version = version.parse(data)

					if curr_version > self.version:

						if os.path.exists('/tmp/install.sh'):
							self.log.info('removing old install.sh')
							os.remove('/tmp/install.sh')

						self.log.info('downloading new install.sh')
						request.urlretrieve(self.INSTALLER_DESCRIPTOR, '/tmp/install.sh')
						self.log.info('chmod /tmp.json/install.sh')
						os.chmod('/tmp/install.sh', 1411)
						# os.system("chmod 777 /tmp.json/install.sh")
						call("sudo ./tmp.json/install.sh")

			except Exception as e:
				self.log.info(e)

			sleep_sec = self.SLEEP_INTERVAL - time.time() % self.SLEEP_INTERVAL
			self.log.info(f'sleep for {round(sleep_sec)} seconds')
			time.sleep(sleep_sec)


if __name__ == '__main__':
	vc = VersionController()
	vc.run()
