"""
  action.py

  This function defines the functions required to complete user actions.
  Highlevel functions that are called by the parsing function will always start
  with the prefix `run_`. Other helper functions are also defined in this file.

  Notice that this file should not not have to handle the sending the signals to
  signal the completion of various signals. This should be handled in the sync.py
  file.
"""
import threading
import time
import json
import re
import os
import sys
import datetime
import subprocess
import paramiko
import traceback
import numpy as np
import ctlcmd.cmdbase as cmdbase

## Importing the global objects as well as the various server helper function.
from . import session
from .sync import *
from .report import *
from .format import *


def run_image_settings(socketio, data):
  """
  Updating the settings for image parsing.
  """
  session.cmd.visual.threshold = float(data['threshold'])
  session.cmd.visual.blur_range = int(data['blur'])
  session.cmd.visual.lumi_cutoff = int(data['lumi'])
  session.cmd.visual.size_cutoff = int(data['size'])
  session.cmd.visual.ratio_cutoff = float(data['ratio']) / 100.0
  session.cmd.visual.poly_range = float(data['poly']) / 100.0
  sync_calibration_settings(socketio)


def run_zscan_settings(socketio, data):
  """
  Updating the setting related to the zscan commands for calibration processes.
  """
  session.zscan_samples = int(data['samples'])
  session.zscan_power_list = [float(x) for x in data['pwm']]
  session.zscan_zlist_dense = [float(z) for z in data['zlist_dense']]
  session.zscan_zlist_sparse = [float(z) for z in data['zlist_sparse']]
  sync_calibration_settings(socketio)


def run_lowlight_settings(socketio, data):
  """
  Updating the settings related to the lowlight calibration process.
  """
  session.lowlight_samples = int(data['samples'])
  session.lowlight_pwm = float(data['pwm'])
  session.lowlight_zval = float(data['zval'])
  sync_calibration_settings(socketio)


def run_lumialign_settings(socketio, data):
  """
  Updating the settings related to the luminosity alignment calibration process.
  """
  session.lumialign_samples = int(data['samples'])
  session.lumialign_pwm = float(data['pwm'])
  session.lumialign_zval = float(data['zval'])
  session.lumialign_range = float(data['range'])
  session.lumialign_distance = float(data['distance'])
  sync_calibration_settings(socketio)


def run_picoscope_settings(socketio, data):
  """
  Updating the settings related to the picoscope readout settings.
  """
  try:
    session.cmd.pico.setrange(0, int(data['channel-a-range']))
    session.cmd.pico.setrange(1, int(data['channel-b-range']))
    session.cmd.pico.settrigger(int(data['trigger-channel']),
                                int(data['trigger-direction']),
                                float(data['trigger-level']),
                                int(data['trigger-delay']), 0)
    session.cmd.pico.setblocknums(int(data['blocksize']), int(
        data['postsample']), int(data['presample']))
    time.sleep(1)
    # Forcing a sleep to make sure commands have been properly processed.
  except Exception as err:
    send_error_message(
        socketio,
        """Error setting up new PICO settings. Make sure picoscope exists.""")
  sync_calibration_settings(socketio)


def run_drs_settings(socketio, data):
  """
  Updating the settings related to the drs readout. Entire thing is
  encapsulated, as the DRS system might not be available.
  """
  try:
    ## The only thing that can be called is a trigger delay.
    # We will be forcing the use of an external trigger
    session.cmd.drs.set_trigger(4, session.cmd.drs.trigger_level(),
                                session.cmd.drs.trigger_direction(),
                                float(data['drs-triggerdelay']))
    session.cmd.drs.set_samples(int(data['drs-samples']))
    session.cmd.drs.set_rate(float(data['drs-samplerate']))
  except Exception as err:
    print(err)
    print(data)
    pass  # TODO: Proper error message for non-existant DRS system
  sync_calibration_settings(socketio)


def run_drs_calib(socketio):
  """
  Running the DRS self calibration program. Here we need to raise a user action
  """
  print("Triggering wait_user_action function")
  wait_user_action(
      socketio,
      """Running the DRS4 self calibration sequence, please make sure all
      physical connectors to the 4 inputs channels are disconnected before
      continuing""")
  print("Running DRS calibration sequence")
  session.cmd.drs.run_calibrations()
  emit_sync_signal(socketio, 'sync-drs-calib-complete', '')


def session_interrupt(socketio):
  """
  Interupting the current command. Notice that this should terminate the
  calibration sequence.
  """
  session.cmd.sighandle.terminate = True


def run_calib_cmd(socketio, cmd, action, detid):
  """
  Running a calibration command. Asside from running the run_single_cmd command
  for updating the command status. There is also the calibration progress bar that needs updating. This is a very thin wrapper around that.
  """

  ## Updating the process tag initially which allow for trigger more stuff
  def set_status(action, detid, status):
    if action not in session.progress_check:
      session.progress_check[action] = {str(detid): status}
    else:
      session.progress_check[action][str(detid)] = status
    send_calib_progress(socketio)

  set_status(action, detid, session.CMD_PENDING)
  set_status(action, detid, session.CMD_RUNNING)
  run_single_cmd(socketio, cmd)
  # Paring the run results:
  if session.run_results == cmdbase.controlcmd.EXIT_SUCCESS:
    set_status(action, detid, session.CMD_COMPLETE)
  elif session.run_results == cmdbase.controlcmd.TERMINATE_CMD:
    set_status(action, detid, session.CMD_ERROR)
    raise KeyboardInterrupt('INTERRUPT SIGNAL RAISED')
  else:
    set_status(action, detid, session.CMD_ERROR)


def run_standard_calibration(socketio, msg):
  """
  Running a standard calibration sequence on an entire board.

  Notice that this assumes that a reference calibration already exists. For each
  detector on the board the standard calibration sequence is as such:
  1. A visual alignment is performed, the transformation matrix is based on the
     reference calibration session.
  2. The sharpness measure is maximized and the corresponding z is recorded.
  3. A intensity v.s. z is measure
  4. The low light performance at a high z is collected.

  Step 3 and 4 will the automatically alternated to minimize the motion time of
  the overall calibration process.
  """
  ## Syning the session type
  sync_session_type(socketio, session.SESSION_TYPE_STANDARD)
  sync_tileboard_type(socketio)
  ## Resetting the cache
  status = prepare_calibration_session(socketio, msg['boardtype'],
                                       msg['boardid'], msg['reference'])
  if status:
    print("FAILED TO PREPARE CALIBRATION SESSION")
    return  ## Early exit on setup failure.

  ## Defining the expected list of processes.
  prepare_progress_check({
      'visalign': session.cmd.board.dets(),
      'zscan': session.cmd.board.dets(),
      'lowlight': session.cmd.board.dets(),
  })

  print("WAITING USER ACTION")
  wait_user_action(socketio, __std_calibration_lighton_msg)
  print("USER ACTION COMPLETE")

  # The visual alignment stuff.
  print('RUNNING VISUAL CALIBARTION')
  set_light('on')
  for detid in session.order_dets:
    line = make_cmd_visualalign(detid)
    run_calib_cmd(socketio, line, 'visalign', detid)
  set_light('off')
  print('VISUAL CALIBRATION COMPLETE')

  wait_user_action(socketio, __std_calibration_lightoff_msg)

  ## Running the luminosity part.
  print("RUNNING LUMINOSITY SCANS")
  for index, detid in enumerate(reversed(session.order_dets)):
    even_line = bool((index % 2) == 0)
    zscan_line = make_cmd_zscan(detid=detid, dense=False, rev=~even_line)
    lowlight_line = make_cmd_lowlight(detid)
    if even_line:
      run_calib_cmd(socketio, zscan_line, 'zscan', detid)
      run_calib_cmd(socketio, lowlight_line, 'lowlight', detid)
    else:
      run_calib_cmd(socketio, lowlight_line, 'lowlight', detid)
      run_calib_cmd(socketio, zscan_line, 'zscan', detid)
  print("EVERYTHING COMPLETE")


## Long message strings are disruptive to code reading are placed here.
__std_calibration_lighton_msg = reduce_cmd_whitespace("""
Starting visual calibration sequences, please make sure the <b>HIGH VOLTAGE
POWER</b> on the SiPM is <b>OFF</b> before continuing!
""")

__std_calibration_lightoff_msg = reduce_cmd_whitespace("""
Starting luminosity calibration sequences, please make sure <b>HIGH VOLTAGE
POWER</b> on the SiPM is <b>ON</b> before continuing!
""")


def run_system_calibration(socketio, msg):
  """
  System calibration with a specified calibration board.

  The processes consists of the the following steps:
  1. The visual calibration matrix is constructed on the first detector in the
     session.
  2. The visual calibration is performed on all detectors in the session.
  3. The light are requested to be turned off and the luminosity alignment is
     performed for all detectors in the session.
  4. For each linear detectors, a luminosity vs. z profile of obtained.
  5. For each counting detector, a low light profile is obtained.

  For system calibration where we expect only a small number of detector
  elements, we will not be optimizing the motion path.
  """
  sync_session_type(socketio, session.SESSION_TYPE_SYSTEM)
  sync_tileboard_type(socketio)
  status = prepare_calibration_session(socketio, msg['boardtype'])
  if status:
    print("FAILED TO SETUP CALIBRATION SESSION")
    return

  ## Defining the expected list of process
  prepare_progress_check({
      'vhscan': [session.order_dets[0]],
      'visalign':
      session.order_dets,
      'lumialign':
      session.order_dets,
      'zscan': [d for d in session.order_dets if (int(d) % 2 == 1)],
      'lowlight': [d for d in session.order_dets if (int(d) % 2 == 0)],
  })

  wait_user_action(socketio, __sys_calibration_lighton_message)

  # Running the visual align stuff.
  set_light('on')
  cmd = make_cmd_visualscan(session.order_dets[0])
  run_calib_cmd(socketio, cmd, 'vhscan', session.order_dets[0])
  for detid in session.cmd.board.dets():
    cmd = make_cmd_visualalign(detid)
    run_calib_cmd(socketio, cmd, 'visalign', detid)
    cmd = make_cmd_vissave(detid)
    run_single_cmd(socketio, cmd)
  set_light('off')

  wait_user_action(socketio, __sys_calibration_lightoff_message)

  ## Running the luminosity alignment
  for detid in session.order_dets:
    cmd = make_cmd_lumialign(detid=detid)
    run_calib_cmd(socketio, cmd, 'lumialign', detid)

  # Generating a luminosity profile from the photo diode on the reference board
  # Otherwise generate a low light profile for a relative efficiency reference.
  for detid in session.order_dets:
    if (int(detid) % 2 == 1):
      cmd = make_cmd_zscan(detid=detid, dense=True, rev=False)
      run_calib_cmd(socketio, cmd, 'zscan', detid)
    else:
      cmd = make_cmd_lowlight(detid=detid)
      run_calib_cmd(socketio, cmd, 'lowlight', detid)

  # At the end of the calibration command, send a signal that tells the client to
  # display the sign off window
  # sync_start_signoff(socketio, 'system')


## Long message strings are disruptive to code reading are placed here.
__sys_calibration_lighton_message = reduce_cmd_whitespace("""
Starting a system calibration process.<br/> Please make sure the reference board
is placed in the correct position, and that the <b>HIGH VOLTAGE POWER</b> for
photo detectors is <b>OFF</b> before continuing!
""")

__sys_calibration_lightoff_message = reduce_cmd_whitespace("""
Starting luminosity scan part of system calibration process, please make sure the
<b>HIGH VOLTAGE POWER</b> for photo detectors is <b>ON</b> before continuing!
""")


def run_process_extend(socketio, msg):
  """
  Extending or remeasuring a certain calibration process for a single detector.
  This command also trigger the additional routines required for updating the
  cached data and the stored progress if needed.
  """
  action = msg['action']
  detid = msg['detid']
  extend = msg['extend']

  # Making the new command to run
  cmd = make_cmd_lumialign(detid) if action == 'lumialign' else \
        make_cmd_lowlight(detid) if action == 'lowlight' else \
        make_cmd_zscan(detid,dense=True,rev=False) if action =='zscan' else \
        make_cmd_visualalign(detid) if action == 'visalign' else \
        ''
  if cmd == '': return  # Early exit if not corresponding command is generated

  cmd = cmd.replace('--wipefile', '') if extend else cmd
  run_calib_cmd(socketio, cmd, action, detid)

  # Updating the visual cache if the action performed is such
  if action == 'visalign':
    cmd = make_cmd_vissave(detid)
    run_single_cmd(socketio, cmd)


def run_calibration_signoff(socketio, data, store):
  """
  Running the process to signoff a calibration result to be saved to the central
  processing server. All data files, as well as the calibration summary, the user
  submitted comment will be packed into a single tar ball to be passed over to
  the central processing server.

  For system calibrations, all stored will be passed over to the calib/ directory
  for future reference.

  For standard calibration processes, an extra comment line is also generated to
  store the reference calibration session.
  """
  ## Saving the calibration results and comments
  run_single_cmd(
      socketio,
      'savecalib -f={filename}'.format(filename=calibration_filename('summary')))

  ## Saving the comment as a json dump.
  comments = {key: data['comments'][key].split('\n') for key in data['comments']}
  if not store: comments['reference'] = session.reference_session
  comment_file = session.cmd.halign.opensavefile(calibration_filename('comment'),
                                                 wipefile=True)
  comment_file.write(json.dumps(comments))

  ## Generating tarball for file transmission
  tar_file = calibration_directory() + '.tar.gz'
  directory = calibration_directory()

  # Making a local copy for future reference
  if store and not os.path.isdir('calib/' + directory):
    subprocess.run(['cp', '-r', directory, 'calib/'])

  # Copying the calibration session over to the data display server over ssh
  subprocess.run(
      ['tar', 'zcvf',
       os.path.basename(tar_file),
       os.path.basename(directory)],
      cwd='results/')
  subprocess.run(['mv', tar_file, os.path.basename(tar_file)])
  tar_file = os.path.basename(tar_file)

  # Copying the data over scp using user login data using paramiko
  counter = 0
  while counter < 5:
    try:
      ssh = paramiko.SSHClient()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect('hepcms-in2.umd.edu',
                  username=data['user'],
                  password=data['pwd'])
      sftp = ssh.open_sftp()
      sftp.banner_timeout = 200000
      sftp.chdir('/data/users/yichen/SiPMCalib/tar')
      print(tar_file, os.path.exists(tar_file))
      sftp.put(tar_file, tar_file)
      sftp.close()
      ssh.close()
      break
    except Exception as e:
      traceback.print_stack()
      send_display_message(socketio, 'Error in ssh connection, trying again...')
      send_display_message(socketio, str(e))
      counter = counter + 1
      time.sleep(2)

  if counter >= 5:
    send_display_message(
        socketio,
        'Failed to transmit file, calibration session is still stored locally')
    return

  ## Cleaning the file in the results directory
  subprocess.run(['rm', '-rf', tar_file])
  subprocess.run(['rm', '-rf', directory])

  clear_cache()
  sync_session_type(socketio, session.SESSION_TYPE_NONE)
  sync_tileboard_type(socketio, clear=True)


def prepare_calibration_session(socketio,
                                boardtype,
                                boardid=None,
                                reference=None):
  """
  Preparing the data members of the global session object for a calibration
  session. This includes:

  1. Loading the boardtype and reference board.
  2. The construction of the data cache map.
  3. Construction of the "ordered list of detectors", this is a very naive
     algorithm aimed to reduce the horizontal motion path required to visit all
     detector. Starting from the 0th detector listed on the board, kee finding
     the closest unvisited neighbor all detectors have been visited.

  If any of the steps fail, the function will return false.
  """
  # Setting up the board
  cmd = 'set --boardtype cfg/{dir}/{type}.json'.format(
      dir='standard' if boardid else 'system', type=boardtype)
  cmd += '  --boardid {id}'.format(id=boardid) if boardid else ''
  status = run_single_cmd(socketio, cmd)
  if (status != 0):
    print("ERROR RUNNING", cmd, "status", status)
    return status
  sync_tileboard_type(socketio)

  # Initializing the data cache.
  session.calib_session_time = datetime.datetime.now()

  # Construction of the ordered list.
  session.order_dets = [list(session.cmd.board.dets())[0]]

  while len(session.order_dets) < len(session.cmd.board.dets()):
    x0, y0 = session.cmd.board.get_det(session.order_dets[-1]).orig_coord
    distance = [{
        'id':
        detid,
        'dist': [
            abs(session.cmd.board.get_det(detid).orig_coord[0] - x0),
            abs(session.cmd.board.get_det(detid).orig_coord[1] - y0)
        ]
    } for detid in session.cmd.board.dets() if detid not in session.order_dets]

    def compare(a):
      return ((a['dist'][0]**2 + a['dist'][1]**2) * 1000 * 1000 +
              a['dist'][0] * 1000 + a['dist'][1])

    next_det = min(distance, key=compare)
    session.order_dets.append(next_det['id'])

  # Since the reference board will contain detectors that doesn't actually exist
  # on the running board, we will run the load calib command last to make sure
  # the board settings doesn't bleed into the file generation.
  if reference:
    session.reference_session = reference
    cmd = 'loadcalib -f calib/{reference}/summary.json'.format(
        reference=reference)
    run_single_cmd(socketio, cmd)
  else:
    session.reference_session = ''

  return 0


def prepare_progress_check(progress_detid):
  """
  Making the progress check map. The input format should be a dictionary in the
  format of:
    { process_tag: detid_list }
  This aims to reduce the verbosity of construction
  """
  session.progress_check = {}
  for tag, id_list in progress_detid.items():
    session.progress_check[tag] = {
        detid: session.CMD_PENDING
        for detid in id_list
    }


def clear_cache():
  session.progress_check = {}
  session.calib_session_time = None
  session.cmd.board.clear()


def set_light(state):
  """
  Thin wrapper around the GPIO lights on/off method. This is for local testing on
  a machine that doesn't have real GPIO control.
  """
  try:
    if state == 'on':
      session.cmd.gpio.light_on()
    else:
      session.cmd.gpio.light_off()
  except:
    pass
