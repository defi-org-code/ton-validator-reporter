import os
from pathlib import Path
import sys
import socket
import json
import time
from datetime import datetime
import logging

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *


class Reporter(object):
	HOME = Path.home()
	RESTRICTED_WALLET_NAME = 'validator_wallet_001'
	WALLET_PATH = f'{HOME}/.local/share/mytoncore/wallets/'
	WALLET_PK_PATH = f'{WALLET_PATH}/{RESTRICTED_WALLET_NAME}.pk'
	WALLET_ADDR_PATH = f'{WALLET_PATH}/{RESTRICTED_WALLET_NAME}.addr'
	MYTONCORE_FILE_PATH = f'{HOME}/.local/share/mytoncore/mytoncore.db'
	REPORTER_DIR = f'/var/ton-validator-reporter'
	REPORTER_PARAMS_FILE = f'{REPORTER_DIR}/params.json'
	MYTONCORE_PATH = '/usr/src'
	REPORTER_FILE = f'{REPORTER_DIR}/report.json'
	orbs_validator_params = dict()
	validation_cycle_in_seconds = None
	LOG_FILENAME = f'{HOME}/.local/share/ton-validator-reporter/out.log'

	SECONDS_IN_YEAR = 365 * 24 * 3600
	SLEEP_INTERVAL = 5 * 60

	def __init__(self):
		super(Reporter, self).__init__()
		self.log = logging
		self.log.basicConfig(format='[%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename=self.LOG_FILENAME)

		self.log.info(f'validator reporter init started at {datetime.utcnow()}')
		self.ton = mytonctrl.MyTonCore()
		self.elector_addr = self.ton.GetFullElectorAddr()
		self.get_set_init_wallet_balance()

	def get_set_init_wallet_balance(self):

		# TODO: create LOG_FILENAME on installer

		# TODO: move to installer script
		if not os.path.isdir(self.REPORTER_DIR):
			self.log.info(f'creating reporter directory at {self.REPORTER_DIR}')
			RunAsRoot(['mkdir', '-m', '777', self.REPORTER_DIR])

		orbs_validator_params = {}
		if os.path.isfile(self.REPORTER_PARAMS_FILE):
			with open(self.REPORTER_PARAMS_FILE, 'r') as f:
				orbs_validator_params = json.load(f)

		if 'wallet_init_balance' not in orbs_validator_params.keys():
			validator_wallet = self.validator_wallet()
			validator_account = self.validator_account(validator_wallet)
			available_validator_balance = self.available_validator_balance(validator_account)
			validator_balance_at_elector = self.balance_at_elector(validator_wallet)

			orbs_validator_params['wallet_init_balance'] = available_validator_balance + validator_balance_at_elector
			self.log.info('orbs_validator_params was updated: ', orbs_validator_params)
			with open(self.REPORTER_PARAMS_FILE, 'w') as f:
				json.dump(orbs_validator_params, f)
				self.log.info(f'{self.REPORTER_PARAMS_FILE} was updated')

		self.orbs_validator_params = orbs_validator_params

	def systemctl_status_validator(self):
		return os.system('systemctl status validator')

	def systemctl_status_validator_ok(self, systemctl_status_validator):
		return int(systemctl_status_validator == 0)

	def restricted_wallet_exists(self):
		return int(os.path.exists(self.WALLET_PK_PATH) and os.path.exists(self.WALLET_ADDR_PATH))

	def validator_index(self):
		return self.ton.GetValidatorIndex()

	def validator_name_ok(self, validator_index):
		return int(socket.gethostname() == f'orbs-{validator_index}')

	def validator_wallet(self):
		return self.ton.GetValidatorWallet()

	def validator_wallet_addr_ok(self, validator_wallet):
		return validator_wallet.addr == self.WALLET_ADDR_PATH

	def validator_account(self, validator_wallet):
		return self.ton.GetAccount(validator_wallet.addr)

	def available_validator_balance(self, validator_account):
		return validator_account.balance

	def balance_at_elector(self, validator_wallet):
		return self.ton.GetReturnedStake(self.elector_addr, validator_wallet)

	def get_local_stake(self):
		return self.ton.GetSettings("stake")

	def get_stats(self):
		return self.ton.GetValidatorStatus()

	def participates_in(self, validator_pubkey):
		cmd = f'runmethodfull {self.elector_addr} participates_in {validator_pubkey}'
		result = self.ton.liteClient.Run(cmd)

	# return self.ton.

	def past_election_ids(self):
		cmd = f'runmethodfull {self.elector_addr} past_election_ids'

		result = self.ton.liteClient.Run(cmd)
		activeElectionId = self.ton.GetVarFromWorkerOutput(result, "result")
		return [int(s) for s in activeElectionId.replace('(', '').replace(')', '').split() if s.isdigit()]

	def active_election_id(self):
		return self.ton.GetActiveElectionId(self.elector_addr)

	def get_mytoncore_db(self):

		with open(self.MYTONCORE_FILE_PATH, 'r') as f:
			return json.load(f)

	def participates_in_election_id(self, mytoncore_db, election_id, wallet_addr):

		if 'saveElections' not in mytoncore_db or election_id not in mytoncore_db['saveElections']:
			return -1

		return int(next((item for item in mytoncore_db['saveElections'][election_id].values() if item['walletAddr'] == wallet_addr), None) is not None)

	def aggregated_apr(self, total_balance, stake_amount):

		if total_balance < stake_amount:
			return 0

		return 100 * (total_balance / self.orbs_validator_params['wallet_init_balance'] - 1)

	def last_cycle_apr(self, local_wallet_balance, stake_amount):
		# we assume here that every cycle we will stake stake_amount (get stake to read this number)
		# and everything is returned to the local wallet
		# we do not use the rewards generated in this process but they are taken in account for the apr calc
		# we should optimize by increase the stake_amount to move from apr to apy
		if stake_amount > local_wallet_balance:
			return 0

		return 100 * (local_wallet_balance / stake_amount - 1) * self.SECONDS_IN_YEAR / self.validation_cycle_in_seconds

	def get_validator_load(self, validator_id):
		# get validator load at index validator_id returns -1 if validator id not found
		# o.w returns the expected and actual blocks created for the last 2000 seconds
		# mr and wr are blocks_created/blocks_expected
		validators_load = self.ton.GetValidatorsLoad()
		if validator_id not in validators_load.keys():
			return -1

		return {
			'mc_blocks_created': validators_load[validator_id]['masterBlocksCreated'],
			'mc_blocks_expected': validators_load[validator_id]['masterBlocksExpected'],
			'wc_blocks_created': validators_load[validator_id]['workBlocksCreated'],
			'wc_blocks_expected': validators_load[validator_id]['workBlocksExpected'],
			'mr': validators_load[validator_id]['mr'],
			'wr': validators_load[validator_id]['wr'],
		}

	def report(self, res):
		with open(self.REPORTER_FILE, 'w') as f:
			json.dump(res, f)

	def run(self):
		res = {}

		while True:

			try:
				self.log.info(f'validator reporter started at {datetime.utcnow()}')
				start_time = time.time()
				systemctl_status_validator = self.systemctl_status_validator()
				res['systemctl_status_validator'] = systemctl_status_validator
				res['systemctl_status_validator_ok'] = self.systemctl_status_validator_ok(systemctl_status_validator)
				res['restricted_wallet_exists'] = self.restricted_wallet_exists()
				validator_index = self.validator_index()
				res['validator_index'] = validator_index
				res['validator_name_ok'] = self.validator_name_ok(validator_index)

				validator_wallet = self.validator_wallet()
				validator_account = self.validator_account(validator_wallet)
				# res['validator_wallet_addr_ok'] = self.validator_wallet_addr_ok(validator_wallet)
				available_validator_balance = self.available_validator_balance(validator_account)
				validator_balance_at_elector = self.balance_at_elector(validator_wallet)
				res['available_validator_balance'] = available_validator_balance
				res['validator_balance_at_elector'] = validator_balance_at_elector
				res['total_validator_balance'] = available_validator_balance + validator_balance_at_elector
				res['local_stake'] = self.get_local_stake()

				stats = self.get_stats()
				res['out_of_sync'] = stats['outOfSync']
				res['is_working'] = int(stats['isWorking'])

				active_election_id = self.active_election_id()
				past_election_ids = self.past_election_ids()
				mytoncore_db = self.get_mytoncore_db()
				res['participate_in_active_election'] = self.participates_in_election_id(mytoncore_db, str(active_election_id), validator_wallet.addr)
				res['participate_in_prev_election'] = self.participates_in_election_id(mytoncore_db, str(max(past_election_ids)), validator_wallet.addr)

				config15 = self.ton.GetConfig15()
				self.validation_cycle_in_seconds = config15['validatorsElectedFor']
				res['last_cycle_apr'] = self.last_cycle_apr(available_validator_balance, res['local_stake'])
				res['aggregated_apr'] = self.aggregated_apr(res['total_validator_balance'], res['local_stake'])
				res['validator_load'] = self.get_validator_load(validator_index)
				self.report(res)
				self.log.info(res)

				self.log.info(datetime.utcnow())
				sleep_sec = self.SLEEP_INTERVAL - time.time() % self.SLEEP_INTERVAL
				self.log.info(f'executed in {round(time.time()-start_time, 2)} seconds')
				self.log.info(f'sleep for {round(sleep_sec)} seconds')
				time.sleep(sleep_sec)

			except Exception as e:
				self.log.info('unexpected error: ', e)
				self.log.info(res)
				sleep_sec = self.SLEEP_INTERVAL - time.time() % self.SLEEP_INTERVAL
				self.log.info(f'sleep for {round(sleep_sec)} seconds')
				time.sleep(sleep_sec)


if __name__ == '__main__':
	reporter = Reporter()
	reporter.run()
