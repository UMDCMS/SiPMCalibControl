"""
  report.py

  Generation of client-side requested data that is not critical to the operation
  of the main system via AJAX requests. The parsing of the AJAX url is done in
  the parsing.py file, this file takes the parsed request type and returns a
  single json-compatible python dictionary for each of the report requests.
"""
import datetime, os, glob, json, re, psutil
from . import session
from .format import *
import numpy as np


def report_system_status():
  """
  Reporting system information that has the user has not directly control over.
  Typically used for system normality diagnostics. These variable will not be
  logged in detail for the underlying system.
  """
  return {
      'start': session.start_time.strftime('%Y/%m/%d/ %H:%M:%S'),
      'time': int(
          (datetime.datetime.now() - session.start_time).total_seconds()),
      ## Constant monitor variables
      'temp1': session.cmd.gpio.ntc_read(0),
      'temp2': session.cmd.gpio.rtd_read(1),
      'volt1': session.cmd.gpio.adc_read(2),
      'volt2': session.cmd.gpio.adc_read(3),
      'coord':
      [session.cmd.gcoder.cx, session.cmd.gcoder.cy, session.cmd.gcoder.cz],
  }


def report_tileboard_layout():
  """
  Reporting a simplified structure of of the calibrated tile board layout, as
  seen using the current session information. Missing calibration information
  will have their coordinates set to (-100,100).
  """
  ans = {
      'boardtype': session.cmd.board.boardtype,
      'detectors': {
          detid: {
              'orig': session.cmd.board.get_det(detid).orig_coord,
              'lumi': session.cmd.board.get_det(detid).orig_coord,
              'vis': session.cmd.board.get_det(detid).orig_coord
          }
          for detid in session.cmd.board.dets()
      }
  }

  for detid in ans['detectors']:
    det = session.cmd.board.get_det(detid)
    ## Updating the visual coordinates if they exists
    if any(det.vis_coord):
      z = min(det.vis_coord.keys())
      ans['detectors'][detid]['vis'] = det.vis_coord[z]
    else:
      ans['detectors'][detid]['vis'] = [-100, -100]

    ## Updating the lumi calibrated coordinates if they exists
    if any(det.lumi_coord):
      z = min(det.lumi_coord.keys())
      ans['detectors'][detid]['lumi'] = [
          det.lumi_coord[z][0], det.lumi_coord[z][2]
      ]
    else:
      ans['detectors'][detid]['lumi'] = [-100, -100]

  return ans


def report_progress():
  """
  Returning the current progress tracking map for the various processes in a
  calibration session.
  """
  return session.progress_check


def report_useraction():
  """
  Returning the message to be displayed in the waiting for user action part.
  """
  return session.waiting_msg


def report_detid_data(process, detid):
  """
  Returning the simplified data via the detector identification. The standard
  naming scheme used by the calibration session will be assumed to extract the
  full filename.
  """
  __default = {}

  try:
    if process == 'zscan':
      fname = calibration_filename('zscan', detid)
      return report_file_data('zscan', fname)
    elif process == 'lowlight':
      fname = calibration_filename('lowlight', detid)
      return report_file_data('hist', fname)
    elif process == 'lumialign':
      fname = calibration_filename('halign', detid)
      return report_file_data('xyz', fname)
    else:
      return __default
  except:
    return __default


def report_system_boards():
  """
  Returning a list a number of boards that can be used for system calibration.
  """
  return get_boards('cfg/system/*.json')


def report_standard_boards():
  """
  Returning a list of board that can be used for standard calibration processes.
  """
  return get_boards('cfg/standard/*.json')


def get_boards(pattern):
  """
  Getting the boards description given a glob pattern
  """
  filelist = glob.glob(pattern)
  ans = {}
  for f in filelist:
    key = os.path.basename(f)
    key = os.path.splitext(key)[0]
    with open(f, 'r') as readfile:
      b = json.load(readfile)
      ans[key] = {
          'name': b['board name'],
          'description': b['board description'],
          'number': len(b['detectors'])
      }
  return ans


def report_valid_reference():
  """
  Returning a list of valid reference with description. This function will look
  in the calib/ directory and find the files that are within 24 hours of the
  request time, for directories that match such a description, the reference
  session formation is packed up into the return json object.
  """
  calib_fmt = re.compile(r'[a-zA-Z\_]+_\d{8}-\d{4}$')
  filelist = [f for f in os.listdir('calib') if calib_fmt.match(f)]

  time_now = datetime.datetime.now()

  ans = []
  for f in filelist:
    time_then = datetime.datetime.strptime(f[-13:], '%Y%m%d-%H%M')
    time_diff = time_now - time_then
    if (time_diff.days + time_diff.seconds / 3600) > 24: continue
    ans.append({
        'tag': f,
        'boardtype': f[:-15],
        'time': time_then.strftime('%Y/%m/%d/ %H:%M:%S')
    })

  # Transformaing input a ordered list to be converted to json format.
  return {'valid': sorted(ans, key=lambda x: x['time'])}


"""
File parsing functions. The following parse file function assumes the following
input:
- f is a file object opened in read mode.
- The file object that it is pointed to assumes the format defined in the
  write_standard_line defined in the cmdbase.savefilecmd method, with the
  following standard columns:
  - timestamp
  - detector id
  - gantry x,y,z
  - pulser bias, 2 temperature readouts,
  - length >2 data array.

The function will then parse the file into a simplified format to be plotted
client side. Notice that no or very little data processing will be handled here.
(Do not expect fitting results and such.)
"""


def parse_file_xyz(f):
  """
  The output to be displayed in a x-y-z heat map. because uncertainties in z is
  difficult to display in heat maps, we will be omitting uncertainties in the
  output.
  """
  ans = {'x': [], 'y': [], 'z': []}

  for line in f:
    tokens = line.split()
    if (len(tokens) != 10): continue  # Skipping over line in bad format.
    ans['x'].append(float(tokens[2]))
    ans['y'].append(float(tokens[3]))
    ans['z'].append(float(tokens[8]))

  return ans


def parse_file_zscan(f):
  """
  This assumes an intensity scale using gantry z motion and the varying values in
  the PWM module. The return value will contain 4 columns, the gantry z position,
  the PWM voltage monitor, the readout value and its uncertainty.
  """
  ans = {'z': [], 'p': [], 'v': [], 'vu': []}
  for line in f:
    tokens = line.split()
    if (len(tokens) != 10): continue  # Skipping over lines with bad format
    ans['z'].append(float(tokens[4]))
    ans['v'].append(float(tokens[8]))
    ans['vu'].append(float(tokens[9]))

  return ans


def parse_file_tscan(f):
  """
  This assumes and intensity scale during for a certain duration of time via the
  timescan command. Notice that the PWM value is intended to vary so it will be
  included in the readout results.
  """
  ans = {'t': [], 'v': [], 'vu': [], 's': [], 'su': []}

  for line in f:
    tokens = line.split()
    if (len(tokens) != 12): continue  # Skipping over lines with bad format
    ans['t'].append(float(tokens[0]))
    ans['v'].append(float(tokens[8]))
    ans['vu'].append(float(tokens[9]))
    ans['s'].append(float(tokens[10]))
    ans['su'].append(float(tokens[11]))

  return ans
