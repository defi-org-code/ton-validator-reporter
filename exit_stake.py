import sys

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *

print('setting stake to 0')

ton = mytonctrl.MyTonCore()
ton.SetSettings("stake", 0)
ton.SetSettings("stakePercent", 0)

stake = ton.GetSettings("stake")
stake_pct = ton.GetSettings("stakePercent")

assert stake == 0, f'stake was not set to 0 {stake}'
assert stake_pct == 0, f'stake percent was not set to 0 {stake_pct}'

print('all done')
