#!/usr/bin/python3 -u
import os
import json
import sys
import argparse

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *
from reporter import Reporter

EMERGENCY_FLAGS_FILE = Reporter.EMERGENCY_FLAGS_FILE


def check_flags_to_reset(flags_to_reset, emergency_flags_from_file):

	if not flags_to_reset:
		return

	assert emergency_flags_from_file, f'trying to delete {flags_to_reset} from empty dict in {EMERGENCY_FLAGS_FILE}'

	for flag in flags_to_reset:
		assert flag in emergency_flags_from_file, f'{flag} not found in {EMERGENCY_FLAGS_FILE}'


def reset_flags(flags_to_reset, emergency_flags_from_file):

	if not flags_to_reset:
		return

	for exit_flag in flags_to_reset:
		while True:
			print(f'delete {exit_flag} from {EMERGENCY_FLAGS_FILE} ? [y/n/q]')
			res = input()
			if res.lower() == 'q':
				print('exit script')
				exit()
			elif res.lower() == 'n':
				print(f'skipping flag {exit_flag}')
			elif res.lower() == 'y':
				del emergency_flags_from_file[exit_flag]
				print(f'{exit_flag} was deleted successfully')
				break

	for exit_flag in emergency_flags_from_file.keys():
		if exit_flag:
			print(f'Warning: {exit_flag} is still set')


def run():

	parser = argparse.ArgumentParser(description='Emergency Flags Reset Script')
	parser.add_argument('-exit_flags', nargs='+', type=str, help='Exit flags list to reset', required=False)
	parser.add_argument('-recovery_flags', nargs='+', type=str, help='Recovery flags list to reset', required=False)
	parser.add_argument('-warning_flags', nargs='+', type=str, help='Warnings flags list to reset', required=False)
	args = parser.parse_args()

	if not args.exit_flags and not args.recovery_flags and not args.warning_flags:
		print('No flags provided, use -h for help')
		exit()

	print('Reset script started')

	reporter = Reporter()
	emergency_flags = reporter.load_json_from_file(EMERGENCY_FLAGS_FILE)

	check_flags_to_reset(args.exit_flags, emergency_flags['exit_flags'])
	check_flags_to_reset(args.recovery_flags, emergency_flags['recovery_flags'])
	check_flags_to_reset(args.warning_flags, emergency_flags['warning_flags'])

	reset_flags(args.exit_flags, emergency_flags['exit_flags'])
	reset_flags(args.recovery_flags, emergency_flags['recovery_flags'])
	reset_flags(args.warning_flags, emergency_flags['warning_flags'])

	reporter.save_json_to_file(emergency_flags, EMERGENCY_FLAGS_FILE)

	print(f'all done')


run()
