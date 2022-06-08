import sys

sys.path.append('/usr/src/mytonctrl')

import mytonctrl
from mypylib.mypylib import *

print('setting stake to 0')

ton = mytonctrl.MyTonCore()
ton.SetSettings("stake", 0)
stake = ton.GetSettings("stake")

assert stake == 0, f'stake was not set to 0 {stake}'

print('all done')
