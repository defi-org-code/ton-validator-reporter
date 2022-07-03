#!/usr/bin/python3 -u
import sys

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *

print('Reset and Enter script started')

ton = mytonctrl.MyTonCore()
stake = 0
stake_percent = 99.99

print(f'setting stake percent to {stake_percent}')
ton.SetSettings("stake", stake)
ton.SetSettings("stakePercent", stake_percent)

assert ton.GetSettings("stakePercent") == stake_percent, f'failed to set stakePercent to {stake_percent}, stakePercent={ton.GetSettings("stakePercent")}'
assert ton.GetSettings("stake") == stake, f'failed to set stake to {stake}, stake={ton.GetSettings("stakePercent")}'

print('all done')
