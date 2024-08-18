#!/usr/bin/python3 -u
import sys

sys.path.append('/usr/src/mytonctrl/mytonctrl')
sys.path.append('/usr/src/mytoncore/mytoncore')

assert len(sys.argv) == 2, 'please provide stake amount'

import mytonctrl
from mypylib.mypylib import *
from mytoncore.mytoncore import MyTonCore

print('Enter script started')

mytoncore_local = MyPyClass('mytoncore.py')
ton = MyTonCore(mytoncore_local)
stake = sys.argv[1]
stake_percent = 0

print(f'setting stake to {stake}')
ton.SetSettings("stake", stake)
print(f'setting stake percent to {stake_percent}')
ton.SetSettings("stakePercent", stake_percent)
print(f'setting usePool to true')
ton.SetSettings("usePool", 'true')

assert ton.GetSettings("stakePercent") == 0, f'failed to set stakePercent to {stake_percent} (stakePercent={ton.GetSettings("stakePercent")})'
assert ton.GetSettings("stake") == int(stake), f'failed to set stake to {stake} (stake={ton.GetSettings("stake")})'
assert ton.GetSettings("usePool") is True, f'failed to set usePool to true (usePool={ton.GetSettings("usePool")})'

# Append stake to file

if stake != 0:
    with open('/home/ubuntu/last-stake', 'w') as f:
        f.write(f'{stake}\n')

print('all done')
