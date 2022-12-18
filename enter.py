#!/usr/bin/python3 -u
import sys

sys.path.append('/usr/src/mytonctrl')

assert len(sys.argv) == 2, 'please provide stake amount'

import mytonctrl
from mypylib.mypylib import *

print('Enter script started')

ton = mytonctrl.MyTonCore()
stake = sys.argv[1]
stake_percent = 'null'

print(f'setting stake to {stake}')
ton.SetSettings("stake", stake)
print(f'setting stake percent to {stake_percent}')
ton.SetSettings("stakePercent", stake_percent)

assert ton.GetSettings("stakePercent") is None, f'failed to set stakePercent to {stake_percent}, stakePercent={ton.GetSettings("stakePercent")}'
assert ton.GetSettings("stake") == int(stake), f'failed to set stake to {stake}, stake={ton.GetSettings("stake")}'

print('all done')
