import argparse
import os
import subprocess
import time
import shutil
import struct
import crc16
import base64


class RestrictedWalletCreator(object):

	def __init__(self):
		super(RestrictedWalletCreator, self).__init__()

		self.restricted_pk_pth = None
		self.restricted_fift_pth = None
		self.start_wallet_id = None
		self.end_wallet_id = None
		self.workchain_id = None
		self.owner_address = None
		self.timeout = None
		self.funding_wallet_path = None
		self.fift = None
		self.lite_client = None
		self.funding_amount = None
		self.wallet_v3_fift = None
		self.funding_wallet_id = None
		self.global_config = None

	def fift_exec(self, cmd):
		print(f'executing fift command: {cmd}')
		process = subprocess.run(cmd.split(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.timeout)
		output = process.stdout.decode("utf-8")
		err = process.stderr.decode("utf-8")
		if len(err) > 0:
			raise Exception("Fift error: {err}".format(err=err))
		print(output)
		return output

	def lite_client_exec(self, cmd):
		print(f'executing lite-client with cmd: {cmd}')
		args = [self.lite_client, "--global-config", self.global_config, "--verbosity", "0", "--cmd", cmd]
		process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=self.timeout)
		output = process.stdout.decode("utf-8")
		err = process.stderr.decode("utf-8")
		if len(err) > 0:
			raise Exception("Lite client error: {err}".format(err=err))

		return output

	def get_seqno(self, addr):

		result = self.lite_client_exec(f'runmethod {addr} seqno')
		if "cannot run any methods" in result:
			return None
		if "result" not in result:
			return 0
		seqno = self.GetVarFromWorkerOutput(result, "result")
		seqno = seqno.replace(' ', '')
		seqno = seqno.replace('[', '')
		seqno = seqno.replace(']', '')
		seqno = int(seqno)
		print(seqno)
		return seqno


	def GetVarFromWorkerOutput(self, text, search):
		if ':' not in search:
			search += ':'
		if search is None or text is None:
			return None
		if search not in text:
			return None
		start = text.find(search) + len(search)
		count = 0
		bcount = 0
		textLen = len(text)
		end = textLen
		for i in range(start, textLen):
			letter = text[i]
			if letter == '(':
				count += 1
				bcount += 1
			elif letter == ')':
				count -= 1
			if letter == ')' and count < 1:
				end = i + 1
				break
			elif letter == '\n' and count < 1:
				end = i
				break
		result = text[start:end]
		if count != 0 and bcount == 0:
			result = result.replace(')', '')
		return result

	def hex_to_base64(self, full_adrr, bounceable=True, testnet=False):
		buff = full_adrr.split(':')
		workchain = int(buff[0])
		addr_hex = buff[1]
		if len(addr_hex) != 64:
			raise Exception("hex_to_base64 error: Invalid length of hexadecimal address")

		b = bytearray(36)
		b[0] = 0x51 - bounceable * 0x40 + testnet * 0x80
		b[1] = workchain % 256
		b[2:34] = bytearray.fromhex(addr_hex)
		buff = bytes(b[:34])
		crc = crc16.crc16xmodem(buff)
		b[34] = crc >> 8
		b[35] = crc & 0xff
		result = base64.b64encode(b)
		result = result.decode()
		result = result.replace('+', '-')
		result = result.replace('/', '_')
		return result

	def binary_addr_to_base64_str(self, file_addr_path):

		file = open(file_addr_path, "rb")
		data = file.read()
		addr_hex = data[:32].hex()
		workchain = struct.unpack("i", data[32:])[0]
		full_addr = str(workchain) + ":" + addr_hex
		base64_addr = self.hex_to_base64(full_addr)
		return base64_addr

	def run(self):
		print('run')

		boc_dir = f'/tmp/restricted_wallets_creator/boc'

		if not os.path.isdir('/tmp/restricted_wallets_creator'):
			os.mkdir('/tmp/restricted_wallets_creator')

		if not os.path.isdir('/tmp/restricted_wallets_creator'):
			os.mkdir(boc_dir)

		output_dir = f'/tmp/restricted_wallets_creator/{time.time()}'
		os.mkdir(output_dir)
		shutil.copy(self.restricted_pk_pth + '.pk', output_dir)

		for wallet_id in range(self.start_wallet_id, self.end_wallet_id):
			print(f'creating restricted wallet {wallet_id} ...')

			# create restricted wallet at workchain-id with wallet-id using pk at restricted_pk_pth
			self.fift_exec(f'{self.fift} -s {self.restricted_fift_pth} {self.workchain_id} {wallet_id} {self.owner_address} {self.restricted_pk_pth}')
			# { ."usage: " $0 type ." <workchain-id> <wallet-id> <owner-address> [<filename-base>]" cr

			# copy restricted addr created at restricted_pk_pth to output dir with {wallet_id}.addr suffix at file name
			shutil.copy(self.restricted_pk_pth + '.addr', output_dir + '/' + self.restricted_pk_pth.split('/')[-1] + f'_{wallet_id}.addr')
			boc_file_path = self.restricted_pk_pth + '-query.boc'
			# shutil.copy(boc_file_path, boc_dir)
			b64_addr = self.binary_addr_to_base64_str(self.restricted_pk_pth + '.addr')
			print(f'Sending {self.funding_amount} TONs to {b64_addr} ...')

			funding_b64 = self.binary_addr_to_base64_str(self.funding_wallet_path + '.addr')
			seqno = self.get_seqno(funding_b64)
			boc_file = f'transfer_{wallet_id}'
			self.fift_exec(f'{self.fift} -s {self.wallet_v3_fift} {self.funding_wallet_path} {b64_addr} {self.funding_wallet_id} {seqno} {self.funding_amount} {boc_file} --timeout 86400')

			self.lite_client_exec(f'sendfile {boc_file}')

			self.lite_client_exec(f'sendfile {boc_file_path}')
			# save restricted wallet address

			# send funds (1 TON) to wallet address

			# deploy wallet

			# update dictionary with wallet address, wallet-id and pk names
			# copy wallet address to output wallets dir

	def init_params(self, parsed_args):

		self.restricted_pk_pth = parsed_args.rwp
		self.restricted_fift_pth = parsed_args.rwf
		self.start_wallet_id = parsed_args.swi
		self.end_wallet_id = parsed_args.ewi
		self.workchain_id = parsed_args.wci
		self.funding_wallet_path = parsed_args.fwp
		self.owner_address = parsed_args.oa
		self.fift = parsed_args.fift
		self.funding_amount = parsed_args.fa
		self.wallet_v3_fift = parsed_args.wv3f
		self.funding_wallet_id = parsed_args.fwi
		self.lite_client = parsed_args.lite_client
		self.global_config = parsed_args.gc

		assert os.path.isfile(self.restricted_pk_pth + '.pk'), f'{self.restricted_pk_pth + ".pk"} does not exists'
		assert os.path.isfile(self.restricted_fift_pth), f'{self.restricted_fift_pth} does not exists'
		assert self.restricted_fift_pth.endswith('.fif'), f'{self.restricted_fift_pth} file should end with .fif extension'
		assert self.start_wallet_id < self.end_wallet_id, 'start_wallet_id should be greater than end_wallet_id'
		assert self.workchain_id in [-1, 0], "workchain_id should be -1 or 0"
		assert os.path.isfile(self.funding_wallet_path + ".pk"), f'{self.funding_wallet_path + ".pk"} does not exists'
		assert os.path.isfile(self.fift), f'{self.fift} does not exists'


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Restricted Wallet Creator')
	parser.add_argument('-rwp', type=str, help='Path to restricted wallet pk', required=True)
	parser.add_argument('-fwp', type=str, help='Path to funding wallet pk, this wallet will pay for deployment', required=True)
	parser.add_argument('-fwi', type=int, help='Funding wallet id, defaults to 698983191', default=698983191)
	parser.add_argument('-rwf', type=str, help='Path to restricted wallet fift code', required=True)
	parser.add_argument('-wv3f', type=str, help='Path to wallet v3 fift code (used for transfer)', required=True)
	parser.add_argument('-swi', type=int, help='Start wallet id, start index of wallet id to create', required=True)
	parser.add_argument('-ewi', type=int, help='End wallet id, end index of wallet id to create', required=True)
	parser.add_argument('-wci', type=int, help='Workchain id, the id of the workchain to generate the restricted wallet, default to 0', default=0)
	parser.add_argument('-oa', type=str, help='Owner address to control the restricted wallet funds', required=True)
	parser.add_argument('-to', type=int, help='timeout for sending .boc files', default=30)
	parser.add_argument('-fa', type=float, help='Funding amount, the amount of TONs to send to each restricted wallet before deployment', default=0.1)
	parser.add_argument('-fift', type=str, help='Path to fift bin', default='/usr/bin/ton/crypto/fift')
	parser.add_argument('-lite-client', type=str, help='Path to lite-client bin', default='/usr/bin/ton/lite-client/lite-client')
	parser.add_argument('-gc', type=str, help='Path to global config', default='/usr/bin/ton/global.config.json')

	args = parser.parse_args()

	rwc = RestrictedWalletCreator()
	rwc.init_params(args)

	rwc.run()
