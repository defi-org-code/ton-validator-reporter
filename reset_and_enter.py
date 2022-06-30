#!/usr/bin/python3 -u
import os
import json
import sys

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *
from reporter import Reporter

REPORTER_DIR = f'/var/reporter'
SOFT_PARAMS_FILE = Reporter.SOFT_PARAMS_FILE


def load_params_from_file():
	if os.path.isfile(SOFT_PARAMS_FILE):
		with open(SOFT_PARAMS_FILE, 'r') as f:
			return json.load(f)


def write_params_to_file(params, key, value):
	params[key] = value

	print(f'writing {key} with value {value} to params file at {SOFT_PARAMS_FILE}')

	with open(SOFT_PARAMS_FILE, 'w') as f:
		json.dump(params, f)
		print(f'{SOFT_PARAMS_FILE} was updated')


print('Reset and Enter script started')

print('Reset soft params are you sure? [y/n]')
res = input()
if res.lower() != 'y':
	print('exit script without any action')
	exit()
else:

	with open(SOFT_PARAMS_FILE, 'w') as f:
		json.dump({}, f)
		print(f'{SOFT_PARAMS_FILE} was reset')

	print(f'restarting reporter service')
	res = os.system('sudo systemctl restart reporter')

	if res != 0:
		print('[ERROR] failed to restart reporter service')
	else:
		print('reporter service restarted successfully')

	print('params file was reset successfully')


ton = mytonctrl.MyTonCore()
stake_percent = 99

print(f'setting stake percent to {stake_percent}')
ton.SetSettings("stakePercent", stake_percent)

assert ton.GetSettings("stakePercent") == stake_percent, f'failed to set stakePercent stakePercent={ton.GetSettings("stakePercent")}'

print('all done')
