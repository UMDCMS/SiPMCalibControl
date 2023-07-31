from cmod.drs import DRS
import time

d = DRS()
d.init()
#d.startcollect()

print("changing trigger delay")
d.settrigger(0, -0.1, 0, 0)

for _ in range(2):
  d.startcollect()
  d.timeslice(0)
  d.read(0)
  d.readraw(0)
  print('')
  #d.read(1)

print("changing trigger delay")
d.settrigger(0, -0.10, 0, 0)
for _ in range(2):
  d.startcollect()
  d.timeslice(0)
  #print('[{x}]'.format(x=_),end='')
  d.read(0)
  #print('[{x}]'.format(x=_),end='')
  d.readraw(0)
  print('')
  #d.read(1)
