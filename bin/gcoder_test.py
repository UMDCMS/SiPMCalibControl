import cmod.gcoder as gcoder
import threading
import time

run_flag = True


def monitor_thread():
  global run_flag
  counter = 0
  while run_flag:
    print("Counter at ", counter)
    counter = counter + 1
    time.sleep(0.1)
  return


if __name__ == "__main__":
  gc = gcoder.GCoder()
  mthread = threading.Thread(target=monitor_thread)
  mthread.start()
  try:
    gc.initprinter("/dev/ttyUSB0")
  except:
    pass
  try:
    gc.moveto(100, 100, 20, False)
  except:
    pass
  time.sleep(1)
  try:
    gc.moveto(10, 10, 1, False)
  except:
    pass
  time.sleep(1)

  run_flag = False
  mthread.join()
