#!/usr/bin/python3 -u
import os
from pathlib import Path
import sys
import socket
import json
import time
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import traceback
from logging import Formatter, getLogger, StreamHandler

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *
from mytoncore import GetMemoryInfo

local = MyPyClass(__file__)


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
	validator_params = dict()
	LOG_FILENAME = f'/var/log/reporter/reporter.log'

	SECONDS_IN_YEAR = 365 * 24 * 3600
	SLEEP_INTERVAL = 1 * 60

	MIN_PROB_NULL = 100

	INIT_BALANCE = 350000

	def __init__(self):
		super(Reporter, self).__init__()

		self.log = self.init_logger()
		self.log.info(f'validator reporter init started at {datetime.utcnow()}')

		self.ton = mytonctrl.MyTonCore()

		self.params = self.load_params_from_file()
		self.init_params()

		self.init_wallet_balance(self.INIT_BALANCE)
		self.init_start_work_time(1655935277)
		self.init_config15()

		self.total_balance = self.params.get('total_balance')
		self.last_cycle_apr = self.params.get('last_cycle_apr')

	def init_logger(self):

		formatter = Formatter(fmt='[%(asctime)s] %(filename)s:%(lineno)s - %(message)s', datefmt='%Y-%m-%d,%H:%M:%S')
		stream_handler = StreamHandler()
		stream_handler.setFormatter(formatter)

		file_handler = RotatingFileHandler(self.LOG_FILENAME, maxBytes=3 * 1024 * 1024, backupCount=5, mode='a')
		file_handler.setFormatter(formatter)

		logger = getLogger('reporter')
		logger.addHandler(stream_handler)
		logger.addHandler(file_handler)
		logger.setLevel(logging.DEBUG)

		return logger

	def load_params_from_file(self):

		if os.path.isfile(self.REPORTER_PARAMS_FILE):
			with open(self.REPORTER_PARAMS_FILE, 'r') as f:
				return json.load(f)

	def write_params_to_file(self, key, value):

		self.params[key] = value

		self.log.info(f'writing {key} with value {value} to params file at {self.REPORTER_PARAMS_FILE}')

		with open(self.REPORTER_PARAMS_FILE, 'w') as f:
			json.dump(self.params, f)
			self.log.info(f'{self.REPORTER_PARAMS_FILE} was updated')

	def init_params(self):

		if not self.params.get('elector_addr'):
			elector_addr = self.ton.GetFullElectorAddr()
			self.write_params_to_file('elector_addr', elector_addr)

		if not self.params.get('config_addr'):
			config_addr = self.ton.GetFullConfigAddr()
			self.write_params_to_file('config_addr', config_addr)

	def init_config15(self):

		config15 = self.ton.GetConfig15()
		if not self.params.get('validators_elected_for'):
			self.write_params_to_file('validators_elected_for', config15['validatorsElectedFor'])

		if not self.params.get('elections_start_before'):
			self.write_params_to_file('elections_start_before', config15['electionsStartBefore'])

		if not self.params.get('elections_end_before'):
			self.write_params_to_file('elections_end_before', config15['electionsEndBefore'])

		if not self.params.get('stake_held_for'):
			self.write_params_to_file('stake_held_for', config15['stakeHeldFor'])

	def init_wallet_balance(self, init_balance):

		if 'wallet_init_balance' not in self.params.keys():

			if not init_balance:
				validator_wallet = self.validator_wallet()
				validator_account = self.validator_account(validator_wallet)
				available_validator_balance = self.available_validator_balance(validator_account)
				init_balance = available_validator_balance

			self.write_params_to_file('wallet_init_balance', init_balance)

	def init_start_work_time(self, start_work_time=None):

		if 'start_work_time' not in self.params.keys():
			start_work_time = start_work_time or time.time()
			self.write_params_to_file('start_work_time', start_work_time)

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
		res = self.ton.liteClient.Run(f'runmethod {wallet.addrB64} wallet_id')
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

	def validator_account(self, validator_wallet):
		return self.ton.GetAccount(validator_wallet.addrB64)

	def available_validator_balance(self, validator_account):
		return validator_account.balance

	def balance_at_elector(self, adnl_addr):
		# get stake from json db
		entries = self.ton.GetElectionEntries()

		if adnl_addr in entries:
			return entries[adnl_addr]['stake']
		else:
			return 0

	def estimate_total_validator_balance(self, mytoncore_db, past_election_ids, adnl_addr, available_validator_balance):

		reported_stakes = list()
		reported_stakes.append(self.get_stake_from_mytoncore_db(mytoncore_db, past_election_ids[0], adnl_addr))
		reported_stakes.append(self.get_stake_from_mytoncore_db(mytoncore_db, past_election_ids[1], adnl_addr))
		reported_stakes.append(self.get_stake_from_mytoncore_db(mytoncore_db, past_election_ids[2], adnl_addr))

		if reported_stakes[0]:
			return sum(reported_stakes[0:2]) + available_validator_balance

		elif reported_stakes[1]:
			return sum(reported_stakes[1:3]) + available_validator_balance

		else:
			# fetch balance from elector as we might sent the funds to elector but mytoncore_db was not updated yet
			return self.balance_at_elector(adnl_addr) + available_validator_balance

	def get_local_stake(self):
		return int(self.ton.GetSettings("stake"))

	def get_local_stake_percent(self):
		return int(self.ton.GetSettings("stakePercent"))

	def get_stats(self):
		return self.ton.GetValidatorStatus()

	def past_election_ids(self, mytoncore_db):
		# cmd = f"runmethodfull {self.params.get('elector_addr')} past_election_ids"
		#
		# result = self.ton.liteClient.Run(cmd)
		# activeElectionId = self.ton.GetVarFromWorkerOutput(result, "result")
		# return sorted([int(s) for s in activeElectionId.replace('(', '').replace(')', '').split() if s.isdigit()], reverse=True)
		return sorted(mytoncore_db['saveElections'].keys(), reverse=True)

	def participate_in_next_validation(self, mytoncore_db, past_election_ids, adnl_addr):
		return int(float(past_election_ids[0]) > time.time() and self.participates_in_election_id(mytoncore_db, str(past_election_ids[0]), adnl_addr))

	def participate_in_curr_validation(self, mytoncore_db, past_election_ids, adnl_addr):

		if float(past_election_ids[0]) < time.time():
			return self.participates_in_election_id(mytoncore_db, str(past_election_ids[0]), adnl_addr)
		else:
			return self.participates_in_election_id(mytoncore_db, str(past_election_ids[1]), adnl_addr)

	def active_election_id(self):
		return self.ton.GetActiveElectionId(self.params.get('elector_addr'))

	def elections_ends_in(self, active_election_id):

		if not active_election_id:
			return 0

		return active_election_id - self.params['elections_end_before']

	def validation_ends_in(self, past_election_ids):

		if float(past_election_ids[0]) > time.time():
			return int((int(past_election_ids[0]) - time.time()) / 60)

		else:
			return int((int(past_election_ids[1]) + int(self.params['validators_elected_for']) - time.time()) / 60)

	def get_mytoncore_db(self):

		with open(self.MYTONCORE_FILE_PATH, 'r') as f:
			return json.load(f)

	def participates_in_election_id(self, mytoncore_db, election_id, adnl_addr):

		if 'saveElections' not in mytoncore_db or election_id not in mytoncore_db['saveElections']:
			return 0

		return int(mytoncore_db['saveElections'][election_id].get(adnl_addr) is not None)

	def get_stake_from_mytoncore_db(self, mytoncore_db, election_id, adnl_addr):

		if 'saveElections' not in mytoncore_db or election_id not in mytoncore_db['saveElections'] or adnl_addr not in mytoncore_db['saveElections'][election_id]:
			return 0

		return int(mytoncore_db['saveElections'][election_id][adnl_addr]['stake'])

	def roi(self, total_balance):

		if not self.params['wallet_init_balance']:
			return 0

		return 100 * (total_balance / self.params['wallet_init_balance'] - 1)

	def apy(self, roi):

		if not roi:
			return 0

		return roi * self.SECONDS_IN_YEAR / (time.time() - self.params['start_work_time'])

	def calc_last_cycle_apr(self, total_balance):

		if not self.total_balance:
			self.total_balance = total_balance
			self.write_params_to_file('total_balance', self.total_balance)
			return None

		if total_balance != self.total_balance:
			validation_cycle_in_seconds = self.params['validators_elected_for']

			roi = 100 * (total_balance / self.total_balance - 1)
			self.total_balance = total_balance
			self.last_cycle_apr = roi * self.SECONDS_IN_YEAR / validation_cycle_in_seconds
			self.write_params_to_file('total_balance', self.total_balance)
			self.write_params_to_file('last_cycle_apr', self.last_cycle_apr)

		return self.last_cycle_apr

	def get_validator_load(self, validator_id, election_id):
		# get validator load at index validator_id returns -1 if validator id not found
		# o.w returns the expected and actual blocks created for the last 2000 seconds
		# mr and wr are blocks_created/blocks_expected
		start_time = int(election_id)
		end_time = int(time.time())-3

		if end_time - start_time > 65536:
			self.log.error(f'unexpected time diff between end_time = {end_time} and start_time = {start_time}')
			start_time = end_time - 3 * 3600  # last 3 hours

		validators_load = self.ton.GetValidatorsLoad(start_time, end_time)
		if validator_id not in validators_load.keys():
			return -1

		return {
			'mc_blocks_created': validators_load[validator_id]['masterBlocksCreated'],
			'mc_blocks_expected': validators_load[validator_id]['masterBlocksExpected'],
			'mc_prob': validators_load[validator_id]['masterProb'],
			'wc_blocks_created': validators_load[validator_id]['workBlocksCreated'],
			'wc_blocks_expected': validators_load[validator_id]['workBlocksExpected'],
			'wc_prob': validators_load[validator_id]['workchainProb'],
			'mr': validators_load[validator_id]['mr'],
			'wr': validators_load[validator_id]['wr'],
		}

	def min_prob(self, validator_load):
		# probability to close <= blocks_created blocks given th eexpected blocks to close are blocks_expected
		if validator_load == -1:
			return self.MIN_PROB_NULL

		return min(validator_load['mc_prob'], validator_load['wc_prob'])

	def check_fine_changes(self, mytoncore_db):

		if 'saveComplaints' not in mytoncore_db:
			return 0

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

		if elector_addr != self.params.get('elector_addr'):
			return 1

		return 0

	def config_addr_changed(self):

		config_addr = self.ton.GetFullConfigAddr()

		if config_addr != self.params.get('config_addr'):
			return 1

		return 0

	def elector_code_changed(self):

		if not self.params.get('elector_addr'):
			return 0

		elector_account = self.ton.GetAccount(self.params.get('elector_addr'))
		assert elector_account, 'failed to get elector account'

		if not self.params.get('elector_code_hash'):
			self.write_params_to_file('elector_code_hash', elector_account.codeHash)
			return 0

		if elector_account.codeHash != self.params.get('elector_code_hash'):
			return 1

		return 0

	def config_code_changed(self):

		if not self.params.get('config_addr'):
			return 0

		config_account = self.ton.GetAccount(self.params.get('config_addr'))
		assert config_account, 'failed to get config account'

		if not self.params.get('config_code_hash'):
			self.write_params_to_file('config_code_hash', config_account.codeHash)
			return 0

		if config_account.codeHash != self.params.get('config_code_hash'):
			return 1

		return 0

	def restricted_addr_changed(self, validator_wallet):

		if not self.params.get('restricted_addr'):
			self.write_params_to_file('restricted_addr', validator_wallet.addrB64)
			return 0

		if validator_wallet.addrB64 != self.params.get('restricted_addr'):
			return 1

		return 0

	def restricted_code_changed(self, validator_account):

		assert validator_account, 'validator account is not set yet'

		if not self.params.get('restricted_code_hash'):
			self.write_params_to_file('restricted_code_hash', validator_account.codeHash)
			return 0

		if validator_account.codeHash != self.params.get('restricted_code_hash'):
			return 1

		return 0

	def get_total_stake(self, mytoncore_db):

		prev_election_id = sorted(mytoncore_db['saveElections'].keys(), reverse=True)[1]
		total_stake = 0
		for values in mytoncore_db['saveElections'][prev_election_id].values():
			total_stake += values['stake']

		return total_stake

	def total_stake_reduced(self, total_stake):

		if not self.params.get('prev_total_stake'):
			self.write_params_to_file('prev_total_stake', total_stake)
			return 0

		return int(total_stake / self.params.get('prev_total_stake') < 0.8)

	def get_num_stakers(self, mytoncore_db):

		prev_election_id = sorted(mytoncore_db['saveElections'].keys(), reverse=True)[1]
		return len(mytoncore_db['saveElections'][prev_election_id].keys())

	def num_stakers_reduced(self, num_stakers):

		if not self.params.get('prev_num_stakers'):
			self.write_params_to_file('prev_num_stakers', num_stakers)
			return 0

		return int(num_stakers / self.params.get('prev_num_stakers') < 0.8)

	def new_offers(self):

		offers = self.ton.GetOffers()

		if self.params.get('offers') is None:
			self.write_params_to_file('offers', offers)
			return 0

		if offers != self.params.get('offers'):
			self.log.info(f'new offers: {offers}, old offers: {self.params.get("offers")} (diff: {list(set(offers) - set(self.params.get("offers")))})')
			return 1

		return 0

	def get_global_version(self):

		config8 = self.ton.GetConfig(8)
		try:
			version = config8['_']['version']
			capabilities = config8['_']['capabilities']
			return version, capabilities

		except Exception as e:
			self.log.error('could not extract version and capabilities from config8={}, e={}'.format(config8, e))
			return -1, -1

	def global_version_changed(self, version, capabilities):

		if not self.params.get('version') or not self.params.get('capabilities'):
			self.write_params_to_file('version', version)
			self.write_params_to_file('capabilities', capabilities)
			return 0

		if version != self.params.get('version') or capabilities != self.params.get('capabilities'):
			return 1

		return 0

	def reporter_pid_changed(self, pid):

		if not self.params.get('reporter_pid'):
			self.write_params_to_file('reporter_pid', pid)
			return 0

		if pid != self.params.get('reporter_pid'):
			return 1

		return 0

	def get_pid(self):
		return os.getpid()

	def exit_next_elections(self):

		self.ton.SetSettings("stake", 0)
		self.ton.SetSettings("stakePercent", 0)

		stake = self.get_local_stake()
		stake_pct = self.get_local_stake_percent()

		if stake != 0 or stake_pct != 0:
			self.log.error(f'Failed to set stake and stake_percent to 0 (stake={stake}, stake_percent={stake_pct})')
		else:
			self.log.info(f'Successfully set stake and stake_percent to 0')

	def recovery_and_alert(self, res):

		res['exit'] = 0
		res['exit_message'] = ''
		res['recovery'] = 0
		res['recovery_message'] = ''
		res['warning'] = 0
		res['warning_message'] = ''

		#################################
		# Exit + Recovery
		#################################
		if res['min_prob'] < .05:
			res['exit'] = 1
			res['recovery'] = 1
			res['exit_message'] += f'min_prob = {res["min_prob"]}; '
			res['recovery_message'] += f'min_prob = {res["min_prob"]}; '

		#################################
		# Exit Only
		#################################
		if res['fine_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'fine_changed = {res["fine_changed"]}; '

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

		if res['total_stake_reduced'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'total_stake_reduced = {res["total_stake_reduced"]}; '

		if res['num_stakers_reduced'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'num_stakers_reduced = {res["num_stakers_reduced"]}; '

		if res['new_offer'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'new_offer = {res["new_offer"]}; '

		if res['sub_wallet_id'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'sub_wallet_id = {res["sub_wallet_id"]}; '

		if res['global_version_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'global_version_changed = {res["global_version_changed"]}; '
		#
		if res['validators_elected_for_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'validators_elected_for_changed = {res["validators_elected_for_changed"]}; '

		if res['elections_start_before_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'elections_start_before_changed = {res["elections_start_before_changed"]}; '

		if res['elections_end_before_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'elections_end_before_changed = {res["elections_end_before_changed"]}; '

		if res['stake_held_for_changed'] != 0:
			res['exit'] = 1
			res['exit_message'] += f'stake_held_for_changed = {res["stake_held_for_changed"]}; '

		if res['reporter_pid_changed'] != 0:
			res['warning'] = 1
			res['warning_message'] += f'reporter_pid_changed = {res["reporter_pid_changed"]}; '

		#################################
		# Recovery Only
		#################################
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

		#################################
		# Set Exit and Recovery message
		#################################
		if res['exit_message'] != '':
			res['exit_message'] = '[EXIT ALERT] ' + res['exit_message']
			self.exit_next_elections()

		if res['recovery_message'] != '':
			res['recovery_message'] = '[RECOVERY ALERT] ' + res['recovery_message']

		if res['warning_message'] != '':
			res['warning_message'] = '[WARNING ALERT] ' + res['warning_message']

	def report(self, res):
		with open(self.REPORTER_FILE, 'w') as f:
			json.dump(res, f)

	def run(self):
		res = {}
		retry = 0

		while True:

			start_time = time.time()
			success = True

			try:
				self.log.info(f'validator reporter started at {datetime.utcnow()} (retry {retry})')
				mytoncore_db = self.get_mytoncore_db()
				self.params = self.load_params_from_file()

				systemctl_status_validator = self.systemctl_status_validator()
				res['systemctl_status_validator'] = systemctl_status_validator
				res['systemctl_status_validator_ok'] = self.systemctl_status_validator_ok(systemctl_status_validator)
				res['restricted_wallet_exists'] = self.restricted_wallet_exists()
				validator_index = self.validator_index()
				res['validator_index'] = validator_index

				validator_wallet = self.validator_wallet()
				validator_account = self.validator_account(validator_wallet)

				adnl_addr = self.ton.GetAdnlAddr()
				res['adnl_addr'] = adnl_addr

				available_validator_balance = self.available_validator_balance(validator_account)
				res['available_validator_balance'] = available_validator_balance

				res['local_stake'] = self.get_local_stake()
				res['local_stake_percent'] = self.get_local_stake_percent()

				stats = self.get_stats()
				res['out_of_sync'] = stats['outOfSync']
				res['is_working'] = int(stats['isWorking'])

				config15 = self.ton.GetConfig15()
				res['validators_elected_for_changed'] = int(config15['validatorsElectedFor'] != self.params['validators_elected_for'])
				res['elections_start_before_changed'] = int(config15['electionsStartBefore'] != self.params['elections_start_before'])
				res['elections_end_before_changed'] = int(config15['electionsEndBefore'] != self.params['elections_end_before'])
				res['stake_held_for_changed'] = int(config15['stakeHeldFor'] != self.params['stake_held_for'])

				past_election_ids = self.past_election_ids(mytoncore_db)
				res['participate_in_next_validation'] = self.participate_in_next_validation(mytoncore_db, past_election_ids, adnl_addr)
				res['participate_in_curr_validation'] = self.participate_in_curr_validation(mytoncore_db, past_election_ids, adnl_addr)
				res['active_election_id'] = self.active_election_id()
				res['elections_ends_in'] = self.elections_ends_in(res['active_election_id'])
				res['validations_ends_in'] = self.validation_ends_in(past_election_ids)

				res['total_validator_balance'] = self.estimate_total_validator_balance(mytoncore_db, past_election_ids, adnl_addr, available_validator_balance)

				res['roi'] = self.roi(res['total_validator_balance'])
				res['apy'] = self.apy(res['roi'])
				res['last_cycle_apr'] = self.calc_last_cycle_apr(res['total_validator_balance'])
				res['validator_load'] = self.get_validator_load(validator_index, str(max(past_election_ids)))
				res['min_prob'] = self.min_prob(res['validator_load'])
				res['fine_changed'] = self.check_fine_changes(mytoncore_db)
				res['net_load_avg'], res['disk_load_pct_avg'], res['mem_load_avg'] = self.get_load_stats(mytoncore_db)

				res['elector_addr_changed'] = self.elector_addr_changed()
				res['config_addr_changed'] = self.config_addr_changed()

				res['elector_code_changed'] = self.elector_code_changed()
				res['config_code_changed'] = self.config_code_changed()

				res['restricted_addr_changed'] = self.restricted_addr_changed(validator_wallet)
				res['restricted_code_changed'] = self.restricted_code_changed(validator_account)

				total_stake = self.get_total_stake(mytoncore_db)

				res['total_stake'] = total_stake

				res['new_offer'] = self.new_offers()

				res['total_stake_reduced'] = self.total_stake_reduced(total_stake)

				num_stakers = self.get_num_stakers(mytoncore_db)
				res['num_stakers'] = num_stakers
				res['num_stakers_reduced'] = self.num_stakers_reduced(num_stakers)

				res['sub_wallet_id'] = self.get_sub_wallet_id(validator_wallet)

				res['version'], res['capabilities'] = self.get_global_version()
				res['global_version_changed'] = self.global_version_changed(res['version'], res['capabilities'])

				pid = self.get_pid()
				res['reporter_pid'] = pid

				res['reporter_pid_changed'] = self.reporter_pid_changed(res['reporter_pid'])

				self.recovery_and_alert(res)

				res['update_time'] = time.time()
				self.report(res)
				self.log.info(res)

				# TODO: last cycle apr, exit + recovery flag in case retry=3

			except Exception as e:
				retry += 1
				success = False
				self.log.info(res)
				self.log.info(f'unexpected error: {e}')
				self.log.info(traceback.format_exc())

			if success or retry >= 3:
				retry = 0
				sleep_sec = self.SLEEP_INTERVAL - time.time() % self.SLEEP_INTERVAL
				self.log.info(f'executed in {round(time.time() - start_time, 2)} seconds')
				self.log.info(f'sleep for {round(sleep_sec)} seconds')
				time.sleep(sleep_sec)


if __name__ == '__main__':
	reporter = Reporter()
	reporter.run()
