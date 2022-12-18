import sys

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *

print('Exit script started')

ton = mytonctrl.MyTonCore()

print('setting stake to null')
ton.SetSettings("stake", 'null')
print('setting stake percent to null')
ton.SetSettings("stakePercent", 'null')

stake = ton.GetSettings("stake")
stake_pct = ton.GetSettings("stakePercent")

assert stake is None, f'stake was not set to 0 {stake}'
assert stake_pct is None, f'stake percent was not set to 0 {stake_pct}'

print('all done')
