#!/usr/bin/python3 -u
import sys

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *

print('Reset and Enter script started')

ton = mytonctrl.MyTonCore()
stake = 'null'
stake_percent = 49.99

print(f'setting stake to {stake}')
ton.SetSettings("stake", stake)
print(f'setting stake percent to {stake_percent}')
ton.SetSettings("stakePercent", stake_percent)

assert ton.GetSettings("stakePercent") == stake_percent, f'failed to set stakePercent to {stake_percent}, stakePercent={ton.GetSettings("stakePercent")}'
assert ton.GetSettings("stake") is None, f'failed to set stake to {stake}, stake={ton.GetSettings("stake")}'

print('all done')
