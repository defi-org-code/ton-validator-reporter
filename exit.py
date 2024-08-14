import sys

sys.path.append('/usr/src/mytonctrl/mytonctrl')
sys.path.append('/usr/src/mytoncore/mytoncore')

import mytonctrl
from mypylib.mypylib import *
from mytoncore.mytoncore import MyTonCore

print('Exit script started')

mytoncore_local = MyPyClass('mytoncore.py')
ton = MyTonCore(mytoncore_local)

print('setting stake to 0')
ton.SetSettings("stake", 0)
print('setting stake percent to 0')
ton.SetSettings("stakePercent", 0)

stake = ton.GetSettings("stake")
stake_pct = ton.GetSettings("stakePercent")

assert stake == 0, f'stake was not set to 0 (stake={stake})'
assert stake_pct == 0, f'stake percent was not set to 0 (stake_pct={stake_pct})'

print('all done')
