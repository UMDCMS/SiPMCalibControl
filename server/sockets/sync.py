"""
  sync.py

  This file contains the functions that handles sending information to the
  clients that is to be initiated server side: Things like the changing of the
  state of the calibration session, message to be passed to the user for display,
  the calibration parameter settings and such. All such function to start with
  the prefix `sync_` to help distinguish function types.

  A second type of "soft", sync message initiated from the server would be the
  `send_` type. While this is sent to the client, it doesn't affect code
  functionality, and can be safely ignore by the client if a corresponding GUI
  element is not present.

  Additional helper function are also defined help with common client/server
  state synchronization. For information to be sent to client-side on client
  request, see the file report.py.
"""
## Commonly used functions
from . import session
from .report import *

import time
import select
import threading
import ctlcmd.cmdbase as cmdbase


def emit_sync_signal(socketio, sync_id, msg):
  """
  All sync signals will use the same namespace and will **always** be
  broadcasted. This helper function helps enforce this behavior, and help with
  reducing the verbosity of function calls.
  """
  socketio.emit(sync_id, msg, namespace='/sessionsocket', boardcast=True)


#################################################################################
"""
Routines common that is commonly used and where client/server side
synchronization is critical such as the execution of a command or waiting for
client side user input.
"""

#################################################################################


def wait_user_action(socketio, msg):
  """
  Setting to system state to waiting for user action with an accompanying
  message. The message is not sent directly, instead relying of client side for
  display. This is what should be used by the high level functions if one need to
  halt the system for user input.
  """
  sync_system_state(socketio, session.STATE_WAIT_USER)
  session.waiting_msg = msg
  time.sleep(0.1)  # Sleep first to system to stabilize
  while (session.state == session.STATE_WAIT_USER):
    time.sleep(0.1)  ## Updating every 0.1 seconds


def complete_user_action(socketio):
  """
  Terminating the wait user state. Function should be called when the server
  receives the complete user action signal. It also wipes the message that is
  stored in session memory.
  """
  print('User action completed')
  sync_system_state(socketio, session.STATE_RUN_PROCESS)
  session.waiting_msg = ""


#################################################################################
"""
Hard sync-like signals. These are typically short, flag-like information needed
to ensure that the client sees the same server state to ensure that operation
correctness.
"""
#################################################################################


def sync_system_state(socketio, new_state):
  """
  Updating the system state of the current calibration session. The various
  action function should all call this function when making changes to the
  system states.
  """
  session.state = new_state
  emit_sync_signal(socketio, 'sync-system-state', session.state)


def sync_session_type(socketio, new_type):
  """
  Updating the system session type of the on-going calibration session. This
  should be the method used by the various action method.
  """
  session.session_type = new_type
  emit_sync_signal(socketio, 'sync-session-type', session.session_type)


def sync_calibration_settings(socketio):
  """
  Sending a sync signal to update all clients that the system settings has
  changed. This should be call at the end of every run_*_settings function. Here
  we are borrowing the report_settings function to reduce code verbosity.
  """
  emit_sync_signal(socketio, 'sync-settings', report_settings())


def sync_tileboard_type(socketio, clear=False):
  """
  Sending the sync signal to indicate which tileboard is currently being stored
  in the calibration session. The client is responsible for generating the
  required HTML elements and additional queries regarding the display results.
  """
  if clear:
    emit_sync_signal(socketio, 'sync-tileboard-type', '')
  else:
    emit_sync_signal(socketio, 'sync-tileboard-type',
                     session.cmd.board.boardtype)


#################################################################################
"""
Soft "send-like" sync signals. Information that can only be updated server side,
but is not critical to the operation of the system.
"""
#################################################################################


def send_cmd_progress(socketio, done=False, error=False):
  """
  Returning a 2-tuple of numbers indicating the progress of the current command.
  to be displayed client side. In case done is set to True, then the command will
  always be return (1,1) or (-1,-1) used to indicate that the command has
  completed (or has erred), otherwise it will look at the current session output
  monitor file and find the string typically used to indicate the command
  progress.
  """
  pattern = re.compile(r'.*\[\s*(\d+)\/\s*(\d+)\]\[.....%\].*')

  def emit(x):
    emit_sync_signal(socketio, 'sync-cmd-progress', x)

  if done:  # Early exists for if the command has be compelted
    if error:
      emit([-1, -1])
      return
    else:
      emit([1, 1])
      return

  if session.state != session.STATE_EXEC_CMD:
    emit([1, 1])
    return

  line = ''
  with open(session.session_output_monitor.name, 'rb') as f:
    """
    Getting the last last line of the output file:
    https://stackoverflow.com/questions/46258499/how-to-read-the-last-line-of-a-file-in-python
    """
    f.seek(-2, os.SEEK_END)
    char = f.read(1)
    while char != b'\n' and char != b'\r' and f.tell() != 0:
      f.seek(-2, os.SEEK_CUR)
      char = f.read(1)

    line = f.readline().decode()  # Getting the last line in the output.

  match = pattern.match(line)
  if match and len(match.groups()) == 2:
    emit([int(match[1]), int(match[2])])
  else:  # Bad matching, don't send new update signal.
    pass  ## Don't try to wipe or update


def send_calib_progress(socketio):
  """
  Passing the signal to the client that the current calibration status has been
  updated.
  """
  print(session.progress_check)
  emit_sync_signal(socketio, 'sync-calib-progress', session.progress_check)


def send_display_message(socketio, msg):
  """
  Sending a single string to handled by the client to be displayed. Notice that
  these strings are not messages stored server side.
  """
  socketio.emit('display-message',
                msg,
                broadcast=True,
                namespace='/sessionsocket')


def send_error_message(socketio, msg):
  """
  Sending a single string to handled by the client to be displayed. Notice that
  these strings are not messages stored server side.
  """
  socketio.emit('display-error', msg, broadcast=True, namespace='/sessionsocket')
