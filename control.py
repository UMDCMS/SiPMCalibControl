#!/usr/bin/env python3
import ctlcmd.cmdbase as cmdbase
import ctlcmd.motioncmd as motioncmd
import ctlcmd.getset as getset
import ctlcmd.digicmd as digicmd
import ctlcmd.viscmd as viscmd
import ctlcmd.picocmd as picocmd
import ctlcmd.drscmd as drscmd
import cmod.fmt as fmt
import logging
import copy
import sys
import traceback
import re

if __name__ == '__main__':
  # Setting the base logger to keep everything
  logging.root.setLevel(logging.NOTSET)

  # Declaring the list of commands that can be used
  cmd = cmdbase.controlterm([
      motioncmd.rungcode,  #
      motioncmd.moveto,  #
      motioncmd.movespeed,  #
      motioncmd.enablestepper,  #
      motioncmd.disablestepper,  #
      motioncmd.sendhome,  #
      motioncmd.halign,  #
      motioncmd.zscan,  #
      motioncmd.lowlightcollect,  #
      motioncmd.timescan,  #
      motioncmd.getcoord,  #
      viscmd.visualset,  #
      viscmd.visualhscan,  #
      viscmd.visualzscan,  #
      viscmd.visualmaxsharp,  #
      viscmd.visualshowdet,  #
      viscmd.visualsaveframe,  #
      viscmd.visualcenterdet,  #
      getset.exit,  #
      getset.set,  #
      getset.get,  #
      getset.history,  #
      getset.logdump,  #
      getset.wait,  #
      getset.savecalib,  #
      getset.loadcalib,  #
      getset.runfile,  #
      digicmd.pulse,  #
      digicmd.pwm,  #
      digicmd.setadcref,  #
      digicmd.showadc,  #
      digicmd.lighton,  #
      digicmd.lightoff,  #
      picocmd.picoset,  #
      picocmd.picorunblock,  #
      picocmd.picorange,  #
      drscmd.drsset,  #
      drscmd.drscalib,  #
      drscmd.drsrun  #
  ])
  # Duplicating the session to allow for default override.
  prog_parser = copy.deepcopy(cmd.set.parser)

  # Augmenting help messages
  prog_parser.prog = 'control.py'
  prog_parser.add_argument('-h',
                           '--help',
                           action='store_true',
                           help='print help message and exit')

  ## Using map to store Default values:
  default_overide = {
      # Devices that can actually switch interfaces with the given string.
      '--printerdev': '/dev/ttyUSB0',
      '--camdev': '/dev/video0',
      # The DRS4 and picoscope CANNOT actually be set by some device string, but
      # requires a fake /dev/ path to be able to trigger the initialization
      # routine
      '--drsdevice': "/dev/MYDRS4",
      '--picodevice': '/dev/MYPICOSCOPE',
  }

  for action in prog_parser._actions:
    for option, default in default_overide.items():
      if option in action.option_strings:
        action.default = default

  args = prog_parser.parse_args()

  if args.help:
    prog_parser.print_help()
    sys.exit(0)

  logger = logging.getLogger("SiPMCalibCMD.setup")
  try:
    logger.info("Running set command")
    cmd.set.run(args)
    logger.info("Starting GPIO")
    cmd.gpio.init()
  except RuntimeError as err:
    logger.error(str(err))
    logger.warning(
        fmt.oneline_string("""
          There was error in the setup process, program will continue but will
          most likely misbehave! Use at your own risk!"""))

  cmd.cmdloop()
  del cmd  # This object requires explicit closing!
