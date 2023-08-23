"""
  format.py

  This file contains a bunch of function that focuses on the formatted strings
  that will be used throughout multiple subroutines.
"""
from . import session

import copy
import datetime


def calibration_directory():
  """
  Making the string represent the callibration storage directory.
  """
  timestamp_string = session.calib_session_time.strftime('%Y%m%d-%H%M')
  return 'results/{boardtype}_{boardid}_{timestamp}'.format(
      boardtype=session.cmd.board.boardtype,
      boardid=session.cmd.board.boardid,
      timestamp=timestamp_string)


def calibration_filename(prefix, detid=None):
  """
  Returning the string corresponding to the filename for a single detector.
  """
  if detid:
    return '{dir}/{prefix}_det{det}.txt'.format(dir=calibration_directory(),
                                                prefix=prefix,
                                                det=detid)
  else:
    return '{dir}/{prefix}.json'.format(dir=calibration_directory(),
                                        prefix=prefix,
                                        det=detid)


def reduce_cmd_whitespace(ans):
  """
  Ensuring that the full command string contains only a single space charactor
  for each whitespace in the string. This ensures that the cmd will not contain
  newlines/tabs that will mess with the command line interface parsing.
  """
  return ' '.join(ans.split())


def make_cmd_zscan(detid, dense, rev):
  """
  Making the command string for running a z-scanning process given the current
  settings of the calibration session.

  You can choose whether the command should run the z dense (for system
  calibration) or sparse (for standard calibration), as well as whether the z
  order should be inverted.
  """
  z_list = copy.copy(session.zscan_zlist_dense) if dense else \
           copy.copy(session.zscan_zlist_sparse)
  ## Whether or not to reverse the ordering
  if rev: z_list = reversed(z_list)

  ans = """
  zscan --detid={detid}
        --channel={channel} --mode={mode}
        --zlist {zlist}
        --sample={samples}
        --power {powerlist}
        --savefile={file}
        --wipefile
  """.format(detid=detid,
             samples=session.zscan_samples,
             mode=session.cmd.board.get_det(detid).mode,
             channel=session.cmd.board.get_det(detid).channel,
             zlist=' '.join([str(z) for z in z_list]),
             powerlist=' '.join([str(p) for p in session.zscan_power_list]),
             file=calibration_filename('zscan', detid))

  return reduce_cmd_whitespace(ans)


def make_cmd_lowlight(detid):
  """
  Making the command string for running the low light collection given the
  settings of the calibration session.
  """
  ans = """
  lowlightcollect --detid {detid}  --sample {samples}
                  --mode={mode}
                  --channel={channel}
                  --power  0.75    -z {zval}
                  --savefile={file}    --wipefile
  """.format(detid=detid,
             samples=session.lowlight_samples,
             mode=session.cmd.board.get_det(detid).mode,
             channel=session.cmd.board.get_det(detid).channel,
             zval=session.lowlight_zval,
             file=calibration_filename('lowlight', detid))

  return reduce_cmd_whitespace(ans)


def make_cmd_lumialign(detid):
  """
  Making the command string for running the luminosity alignment process given
  the settings of the calibration session.
  """
  ans = """
  halign --detid={detid}
         --channel={channel} --mode={mode}
         --sample={samples} -z {zval}  --overwrite
         --range={range} --distance={distance}
         -f={filename}
         --power={power}
         --wipefile
  """.format(detid=detid,
             mode=session.cmd.board.get_det(detid).mode,
             channel=session.cmd.board.get_det(detid).channel,
             samples=session.lumialign_samples,
             zval=session.lumialign_zval,
             range=session.lumialign_range,
             distance=session.lumialign_distance,
             filename=calibration_filename('halign', detid),
             power=session.lumialign_pwm)
  return reduce_cmd_whitespace(ans)


def make_cmd_visualalign(detid):
  """
  making the command string for running the visual alignment process given the
  settings of the calibration session.
  """
  ans = """
  visualcenterdet --detid {detid} -z {zval} --overwrite
  """.format(detid=detid, zval=session.visual_zval)
  return reduce_cmd_whitespace(ans)


def make_cmd_visualscan(detid):
  """
  Making the command string for running the visual matrix construction given the
  settings of the calibration session.
  """
  ans = """
  visualhscan --detid={detid} -z {zval} --range 3 --distance 1 --overwrite
              -f=/dev/null
  """.format(detid=detid, zval=session.visual_zval)
  return reduce_cmd_whitespace(ans)


def make_cmd_vissave(detid):
  """
  Making the command required to save the visual alignment results to a standard
  postion.
  """
  ans = """
  visualsaveframe --saveimg {file}
  """.format(
      file=calibration_filename('visualalign', detid).replace('.txt', '.jpg'))
  return reduce_cmd_whitespace(ans)