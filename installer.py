from urllib import request
import json
import os
from git import Repo
from wget import  download

DESCRIPTORS = {'main': 'https://raw.githubusercontent.com/defi-org-code/ton-validator-reporter/master/main.py'}
REPORTER_DIR = f'/var/ton-validator-reporter'
SRC_DIR = f'/usr/src/ton-validator-reporter'


def install():
	# run as sudo
	# r = Repo.clone_from(DESCRIPTOR, '/tmp/mng')
	# print(r)
	# return

	# create /var/ton-validator-reporter/ dir
	if not os.path.isdir(REPORTER_DIR):
		print(f'creating reporter directory at {REPORTER_DIR}')
		os.mkdir(REPORTER_DIR, 777)

	# create /usr/src/ton-validator-reporter/ dir
	if not os.path.isdir(SRC_DIR):
		print(f'creating reporter directory at {SRC_DIR}')
		os.mkdir(SRC_DIR, 777)

	download(DESCRIPTORS['main'])
	# download source to /usr/src/ton-validator-reporter/version-controller.py
	# download source to /usr/src/ton-validator-reporter/main.py

	# download ton-validator-reporter.service to /etc/systemd/system/
	# download ton-validator-version-ctrl.service to /etc/systemd/system/
	# systemd reload, start service

	# create log file

	# other tasks...

	# with request.urlopen(DESCRIPTOR) as url:
	# 	data = json.loads(url.read().decode())
	# 	print(data)
	#

install()
