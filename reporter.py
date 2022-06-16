#!/usr/bin/python3 -u
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
from mytoncore import GetMemoryInfo


class Reporter(object):
	HOME = Path.home()
	RESTRICTED_WALLET_NAME = 'validator_wallet_001'
	WALLET_PATH = f'{HOME}/.local/share/mytoncore/wallets/'
	WALLET_PK_PATH = f'{WALLET_PATH}/{RESTRICTED_WALLET_NAME}.pk'
	WALLET_ADDR_PATH = f'{WALLET_PATH}/{RESTRICTED_WALLET_NAME}.addr'
	MYTONCORE_FILE_PATH = f'{HOME}/.local/share/mytoncore/mytoncore.db'
	REPORTER_DIR = f'/var/reporter'
	REPORTER_PARAMS_FILE = f'{REPORTER_DIR}/params.json'
	MYTONCORE_PATH = '/usr/src'
	REPORTER_FILE = f'{REPORTER_DIR}/report.json'
	orbs_validator_params = dict()
	validation_cycle_in_seconds = None
	LOG_FILENAME = f'/var/log/reporter/reporter.log'

	SECONDS_IN_YEAR = 365 * 24 * 3600
	SLEEP_INTERVAL = 1 * 60

	MIN_EFFICIENCY_NULL = 100

	def __init__(self):
		super(Reporter, self).__init__()

		logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)s - %(message)s', datefmt='%m-%d-%Y %H:%M:%S.%f', filename=self.LOG_FILENAME, level=logging.INFO)
		self.log = logging

		self.elector_addr = None
		self.config_addr = None
		self.elector_code_hash = None
		self.config_code_hash = None
		self.restricted_addr = None
		self.restricted_code_hash = None
		self.prev_total_stake = None
		self.prev_num_stakers = None
		self.offers = []

		self.log.info(f'validator reporter init started at {datetime.utcnow()}')
		self.ton = mytonctrl.MyTonCore()
		self.elector_addr = self.ton.GetFullElectorAddr()
		self.get_set_init_wallet_balance()

	def get_set_init_wallet_balance(self):

		# TODO: create LOG_FILENAME on installer

		orbs_validator_params = {}
		if os.path.isfile(self.REPORTER_PARAMS_FILE):
			with open(self.REPORTER_PARAMS_FILE, 'r') as f:
				orbs_validator_params = json.load(f)

		if 'wallet_init_balance' not in orbs_validator_params.keys():
			validator_wallet = self.validator_wallet()
			print(f'validator_wallet.addr={validator_wallet.addr}')
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

	def validator_name_ok(self, wallet_id):
		return int(socket.gethostname() == f'validator-{wallet_id}')

	def get_sub_wallet_id(self, wallet):
		res = self.ton.liteClient.Run(f'runmethod {wallet.addr} wallet_id')
		self.log.info(res)
		res = self.ton.GetVarFromWorkerOutput(res, "result")

		if not res:
			return -1

		try:
			res = int((res.replace('[', '').replace(']', '').split())[0])
			return res
		except Exception as e:
			self.log.info(f'error: unable to extract wallet_id: {e}')
			return -1

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

	def aggregated_apr(self, total_balance, stake_amount, min_stake_amount=315000):

		if stake_amount and total_balance and (total_balance < stake_amount or stake_amount < min_stake_amount):
			return 0

		return 100 * (total_balance / self.orbs_validator_params['wallet_init_balance'] - 1)

	def last_cycle_apr(self, local_wallet_balance, stake_amount, min_stake_amount=315000):
		# we assume here that every cycle we will stake stake_amount (get stake to read this number)
		# and everything is returned to the local wallet
		# we do not use the rewards generated in this process (stake is not increased every validation cycle) but they are taken in account for the apr calc
		# we should optimize by increase the stake_amount to move from apr to apy
		if stake_amount and local_wallet_balance and (stake_amount > local_wallet_balance or stake_amount < min_stake_amount):
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

	def calc_min_efficiency(self, validator_load):

		if validator_load == -1:
			return self.MIN_EFFICIENCY_NULL

		return min(validator_load['mr'], validator_load['wr'])

	def check_fine_changes(self, mytoncore_db):

		complaints_hash = []
		last_reported_election = sorted(mytoncore_db['saveComplaints'].keys(), reverse=True)[0]
		for complaint_hash, complaints_values in mytoncore_db['saveComplaints'][last_reported_election].items():
			if complaints_values['suggestedFine'] != 101.0 or complaints_values['suggestedFinePart'] != 0.0:
				complaints_hash.append(complaint_hash)

		return complaints_hash or 0

	def get_load_stats(self, mytoncore_db):

		net_load_avg = mytoncore_db['statistics']['netLoadAvg'][1]
		sda_load_avg_pct = mytoncore_db['statistics']['disksLoadPercentAvg']['sda'][1]
		sdb_load_avg_pct = mytoncore_db['statistics']['disksLoadPercentAvg']['sdb'][1]
		disk_load_pct_avg = max(sda_load_avg_pct, sdb_load_avg_pct)

		mem_info = GetMemoryInfo()
		mem_load_avg = mem_info['usagePercent']

		return net_load_avg, disk_load_pct_avg, mem_load_avg

	def elector_addr_changed(self):

		elector_addr = self.ton.GetFullElectorAddr()

		elector_addr_changed = 0
		if self.elector_addr is not None and elector_addr != self.elector_addr:
			elector_addr_changed = 1

		self.elector_addr = elector_addr

		return elector_addr_changed

	def config_addr_changed(self):

		config_addr = self.ton.GetFullConfigAddr()

		config_addr_changed = 0
		if self.config_addr and config_addr != self.config_addr:
			config_addr_changed = 1

		self.config_addr = config_addr

		return config_addr_changed

	def elector_code_changed(self):

		if not self.elector_addr:
			return 0

		elector_account = self.ton.GetAccount(self.elector_addr)
		assert elector_account, 'failed to get elector account'

		if not self.elector_code_hash:
			self.elector_code_hash = elector_account.codeHash
			return 0

		if elector_account.codeHash != self.elector_code_hash:
			return 1

		return 0

	def config_code_changed(self):

		if not self.config_addr:
			return 0

		config_account = self.ton.GetAccount(self.config_addr)
		assert config_account, 'failed to get config account'

		if not self.config_code_hash:
			self.config_code_hash = config_account.codeHash
			return 0

		if config_account.codeHash != self.config_code_hash:
			return 1

		return 0

	def restricted_addr_changed(self, validator_wallet):

		restricted_addr_changed = 0
		if self.restricted_addr is not None and validator_wallet.addr != self.restricted_addr:
			restricted_addr_changed = 1

		self.restricted_addr = validator_wallet.addr

		return restricted_addr_changed

	def restricted_code_changed(self, validator_account):

		if not self.restricted_addr:
			return 0

		assert validator_account, 'failed to get validator account'

		if not self.restricted_code_hash:
			self.restricted_code_hash = validator_account.codeHash
			return 0

		if validator_account.codeHash != self.restricted_code_hash:
			return 1

		return 0

	def get_total_stake(self, mytoncore_db):

		prev_election_id = sorted(mytoncore_db['saveElections'].keys(), reverse=True)[1]
		total_stake = 0
		for values in mytoncore_db['saveElections'][prev_election_id].values():
			total_stake += values['stake']

		return total_stake

	def total_stake_reduce(self, total_stake):

		if not self.prev_total_stake:
			self.prev_total_stake = total_stake
			return 0

		prev_total_stake = self.prev_total_stake
		self.prev_total_stake = total_stake

		return int(total_stake / prev_total_stake < 0.8)

	def get_num_stakers(self, mytoncore_db):

		prev_election_id = sorted(mytoncore_db['saveElections'].keys(), reverse=True)[1]
		return len(mytoncore_db['saveElections'][prev_election_id].keys())

	def num_stakers_reduce(self, num_stakers):

		if not self.prev_num_stakers:
			self.prev_num_stakers = num_stakers
			return 0

		prev_num_stakers = self.prev_num_stakers
		self.prev_num_stakers = prev_num_stakers

		return int(num_stakers / prev_num_stakers < 0.8)

	def new_offers(self):

		offers = self.ton.GetOffers()

		if not self.offers:
			self.offers = offers
			return 0

		if offers != self.offers:
			self.log.info(f'new offers: {offers}, old offers: {self.offers} (diff: {list(set(offers)- set(self.offers))})')
			return 1

	def recovery_and_alert(self, res):

		res['exit'] = 0
		res['exit_message'] = ''
		res['recovery'] = 0
		res['recovery_message'] = ''

		if res['min_efficiency'] < .85:
			res['exit'] = 1
			res['recovery'] = 1
			res['exit_message'] += f'min_efficiency = {res["min_efficiency"]}; '
			res['recovery_message'] += f'min_efficiency = {res["min_efficiency"]}; '

		if res['fine_changed'] != 0:
			res['exit'] = 1
			res['recovery'] = 1
			res['exit_message'] += f'fine_changed = {res["fine_changed"]}; '
			res['recovery_message'] += f'fine_changed = {res["fine_changed"]}; '

		if res['elector_addr_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'elector_addr_changed = {res["elector_addr_changed"]}; '

		if res['config_addr_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'config_addr_changed = {res["config_addr_changed"]}; '

		if res['elector_code_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'elector_code_changed = {res["elector_code_changed"]}; '

		if res['config_code_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'config_code_changed = {res["config_code_changed"]}; '

		if res['restricted_addr_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'restricted_addr_changed = {res["restricted_addr_changed"]}; '

		if res['restricted_code_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'restricted_code_changed = {res["restricted_code_changed"]}; '

		if res['total_staked_reduce'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'total_staked_reduce = {res["total_staked_reduce"]}; '

		if res['num_stakers_reduce'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'num_stakers_reduce = {res["num_stakers_reduce"]}; '

		if res['validator_name_ok'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'validator_name_ok = {res["validator_name_ok"]}; '

		if res['systemctl_status_validator_ok'] != 1:
			res['recovery'] = 1
			res['recovery_message'] += f'systemctl_status_validator_ok = {res["systemctl_status_validator_ok"]}; '

		if res['out_of_sync'] > 50:
			res['recovery'] = 1
			res['recovery_message'] += f'out_of_sync = {res["out_of_sync"]}; '

		if res['mem_load_avg'] > 85:
			res['recovery'] = 1
			res['recovery_message'] += f'mem_load_avg = {res["mem_load_avg"]}; '

		if res['disk_load_pct_avg'] > 85:
			res['recovery'] = 1
			res['recovery_message'] += f'disk_load_pct_avg = {res["disk_load_pct_avg"]}; '

		if res['net_load_avg'] > 400:
			res['recovery'] = 1
			res['recovery_message'] += f'net_load_avg = {res["net_load_avg"]}; '

		if res['exit_message'] != '':
			res['exit_message'] = '[EXIT ALERT] ' + res['exit_message']

		if res['recovery_message'] != '':
			res['recovery_message'] = '[RECOVERY ALERT] ' + res['recovery_message']

	def report(self, res):
		with open(self.REPORTER_FILE, 'w') as f:
			json.dump(res, f)

	def run(self):
		res = {}

		while True:

			start_time = time.time()

			# try:
			self.log.info(f'validator reporter started at {datetime.utcnow()}')
			systemctl_status_validator = self.systemctl_status_validator()
			res['systemctl_status_validator'] = systemctl_status_validator
			res['systemctl_status_validator_ok'] = self.systemctl_status_validator_ok(systemctl_status_validator)
			res['restricted_wallet_exists'] = self.restricted_wallet_exists()
			validator_index = self.validator_index()
			res['validator_index'] = validator_index

			print('1')
			validator_wallet = self.validator_wallet()
			validator_account = self.validator_account(validator_wallet)
			# res['validator_wallet_addr_ok'] = self.validator_wallet_addr_ok(validator_wallet)
			available_validator_balance = self.available_validator_balance(validator_account)
			validator_balance_at_elector = self.balance_at_elector(validator_wallet)
			res['available_validator_balance'] = available_validator_balance
			res['validator_balance_at_elector'] = validator_balance_at_elector
			res['total_validator_balance'] = available_validator_balance + validator_balance_at_elector
			res['local_stake'] = self.get_local_stake()
			print('2')

			stats = self.get_stats()
			res['out_of_sync'] = stats['outOfSync']
			res['is_working'] = int(stats['isWorking'])
			print('3')

			active_election_id = self.active_election_id()
			past_election_ids = self.past_election_ids()
			mytoncore_db = self.get_mytoncore_db()
			res['participate_in_active_election'] = self.participates_in_election_id(mytoncore_db, str(active_election_id), validator_wallet.addr)
			res['participate_in_prev_election'] = self.participates_in_election_id(mytoncore_db, str(max(past_election_ids)), validator_wallet.addr)
			print('4')

			config15 = self.ton.GetConfig15()
			self.validation_cycle_in_seconds = config15['validatorsElectedFor']
			res['last_cycle_apr'] = self.last_cycle_apr(available_validator_balance, res['local_stake'])
			res['aggregated_apr'] = self.aggregated_apr(res['total_validator_balance'], res['local_stake'])
			res['validator_load'] = self.get_validator_load(validator_index)
			res['min_efficiency'] = self.calc_min_efficiency(res['validator_load'])
			res['fine_changed'] = self.check_fine_changes(mytoncore_db)
			res['net_load_avg'], res['disk_load_pct_avg'], res['mem_load_avg'] = self.get_load_stats(mytoncore_db)
			print('5')

			res['elector_addr_changed'] = self.elector_addr_changed()
			res['config_addr_changed'] = self.config_addr_changed()
			print('6')

			res['elector_code_changed'] = self.elector_code_changed()
			res['config_code_changed'] = self.config_code_changed()
			print('7')

			res['restricted_addr_changed'] = self.restricted_addr_changed(validator_wallet)
			res['restricted_code_changed'] = self.restricted_code_changed(validator_account)
			print('8')

			total_stake = self.get_total_stake(mytoncore_db)
			print('9')

			res['total_stake'] = total_stake

			res['new_offer'] = self.new_offers()

			res['total_staked_reduce'] = self.total_stake_reduce(total_stake)

			num_stakers = self.get_num_stakers(mytoncore_db)
			res['num_stakers'] = num_stakers
			res['num_stakers_reduce'] = self.num_stakers_reduce(num_stakers)

			wallet_id = self.get_sub_wallet_id(validator_wallet)
			res['validator_name_ok'] = self.validator_name_ok(wallet_id)

			self.recovery_and_alert(res)

			# TODO: owner getter check

			# TODO: reporter restart (lifetime decreased)
			# TODO: validator restart (lifetime decreased)
			# TODO: check log max size, rotation?
			# TODO: how to check if network was upgraded (exit on any change)

			# TODO: Restricted wallet - separate rewards from funds (legal) -> shlomi

			res['update_time'] = time.time()
			self.report(res)
			self.log.info(res)

			# except Exception as e:
			# 	self.log.info(f'unexpected error: {e}')
			# 	self.log.info(res)

			sleep_sec = self.SLEEP_INTERVAL - time.time() % self.SLEEP_INTERVAL
			self.log.info(f'executed in {round(time.time()-start_time, 2)} seconds')
			self.log.info(f'sleep for {round(sleep_sec)} seconds')
			time.sleep(sleep_sec)


if __name__ == '__main__':
	reporter = Reporter()
	reporter.run()
