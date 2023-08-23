"""
  parsing.py

  Functions here are directly called by the socketio object via the decorated
  methods in the __init__.py file. The parses the socketio data stream, then call
  the required function split across the various files for the sake of clarity.
"""
import threading
import datetime
import time
import cv2
import io

from . import session
from .action import *
from .report import *
from .sync import *


def socket_connect(socketio):
  """
  Process to execute when client first connects. Immediately the system state is
  updated to all clients. All other information will be handled by client
  request. This will also start the socket session for passing through the
  terminal session via the xterm.js socketio interface. The terminal_passthrough
  methods is defined in the sync method.
  """
  print('Socket connected')
  sync_system_state(socketio, session.state)
  sync_session_type(socketio, session.session_type)
  sync_tileboard_type(socketio)
  send_cmd_progress(socketio)
  send_calib_progress(socketio)


def resend_sync(socketio, msg):
  """
  Client-side request for resending a sync signal.
  """
  if msg == 'state':
    sync_system_state(socketio, session.state)
  elif msg == 'tileboard':
    sync_tileboard_type(socketio)
  elif msg == 'progress':
    send_calib_progress(socketio)
  else:
    print('Unrecognized request')


def run_action(socketio, msg):
  """
  Processing of user action input. The whole action will wrapped in a try
  statement. In case any exception is raised, the function will still return the
  session into a user useable state, the exception message is passed back to the
  user session for the client to determine how the message should be handled.
  """
  if session.state != session.STATE_IDLE:
    send_error_message(socketio, 'CANNOT RUN ACTION, REQUEST ALREADY IN PLACE')
    return

  sync_system_state(socketio, session.STATE_RUN_PROCESS)

  try:
    ## Standardized calibration sequences. Functions are defined in action.py
    if msg['id'] == 'run-std-calibration':
      run_standard_calibration(socketio, msg['data'])
    elif msg['id'] == 'run-system-calibration':
      run_system_calibration(socketio, msg['data'])
    elif msg['id'].endswith('calibration-signoff'):
      run_calibration_signoff(socketio, msg['data'],
                              msg['id'].startswith('system'))
    elif msg['id'] == 'rerun-single':
      run_process_extend(socketio, msg['data'])
    elif msg['id'] == 'image-settings':
      run_image_settings(socketio, msg['data'])
    elif msg['id'] == 'zscan-settings':
      run_zscan_settings(socketio, msg['data'])
    elif msg['id'] == 'lowlight-settings':
      run_lowlight_settings(socketio, msg['data'])
    elif msg['id'] == 'lumialign-settings':
      run_lumialign_settings(socketio, msg['data'])
    elif msg['id'] == 'picoscope-settings':
      run_picoscope_settings(socketio, msg['data'])
    elif msg['id'] == 'drs-settings':
      run_drs_settings(socketio, msg['data'])
    elif msg['id'] == 'drs-calib':
      run_drs_calib(socketio)  ## Data less command.
    else:
      send_error_message(socketio, f'Unsupported action item {msg["id"]}')
      print(msg)
      time.sleep(5)
  except Exception as e:
    send_error_message(socketio, str(e))

  sync_system_state(socketio, session.STATE_IDLE)


def send_interrupt(socketio):
  """
  Sending effectively the interupt signal to the underlying command line object.
  """
  session_interrupt(socketio)  # action.py


def get_file_data(process, filename):
  """
  Returning the cached data of the a the given process defined by the process. To
  help with code structure uniformity. This function will just be a thin wrapper
  around the report_cached_data method defined in the report.py file (since the
  function formatting is similar to a typical reporting process)
  """
  return report_file_data(process, filename.replace('@', '/'))


def get_detid_data(process, detid):
  """
  Returning the cached data of the a the given process defined by the process. To
  help with code structure uniformity. This function will just be a thin wrapper
  around the report_cached_data method defined in the report.py file (since the
  function formatting is similar to a typical reporting process)
  """
  return report_detid_data(process, detid)
