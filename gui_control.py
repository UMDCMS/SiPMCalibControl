#!/usr/bin/env python3
"""
Script used to initiate the GUI server instance. The main documentation will be
given in the files of the server/ directory
"""
import gui.server.session as ss
import ctlcmd.cmdbase as cmdbase
import ctlcmd.motioncmd as motioncmd
import ctlcmd.getset as getset
import ctlcmd.digicmd as digicmd
import ctlcmd.viscmd as viscmd
import ctlcmd.picocmd as picocmd
import ctlcmd.drscmd as drscmd
import cmod.fmt as fmt
import logging  # Additional settings required
import copy

if __name__ == '__main__':
  logging.root.setLevel(
      logging.NOTSET)  # Setting the base logger to keep everything

  # Creating the sessoin instance
  """
  session = ss.GUISession([
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
      # viscmd.visualshowdet,  # Should not try to create image window
      viscmd.visualsaveframe,  #
      viscmd.visualcenterdet,  #
      # getset.exit,  # Should not exit program via this path.
      getset.set,  #
      getset.get,  #
      getset.history,  #
      # getset.logdump,  # Should not attempt to dump log like this
      getset.wait,  #
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
  """

  session = ss.GUISession([getset.set, getset.get, getset.wait, ss.shutdown])

  # Duplicating the session to allow for default override.
  prog_parser = copy.deepcopy(session.cmd.set.parser)

  # Augmenting help messages
  prog_parser.prog = 'gui_control.py'
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
    session.cmd.set.run(args)
  except Exception as err:
    logger.error(str(err))
    logger.warning(
        fmt.oneline_string("""
          There was error in the device setup process, program will continue but
          will most likely misbehave! Use at your own risk!"""))
  try:
    logger.info("Starting GPIO")
    session.cmd.gpio.init()
  except Exception as err:
    logger.error(str(err))
    logger.warning(
        fmt.oneline_string("""
          There was error in the GPIO setup, program will continue but will most
          likely misbehave! Use at your own risk!"""))

  session.start_session()  # Starting the session!
  # Notice that this will continue to run until the shutdown signal is sent from
  # a client side request.

  # Currently this seg-faults on exit. I am not sure which hardware interface is
  # not being released properly, but doesn't seem to cause any persistent issue
  # as far as I can tell.
  del session
