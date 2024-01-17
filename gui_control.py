#!/usr/bin/env python3
"""
Script used to initiate the GUI server instance. The main documentation will be
given in the files of the server/ directory
"""

import gui.server.session as ss

import ctlcmd.cmdbase as cmdbase
#import ctlcmd.gcodercmd as gcodercmd
#import ctlcmd.digicmd as digicmd
#import ctlcmd.visualcmd as visualcmd
#import ctlcmd.picocmd as picocmd
#import ctlcmd.drscmd as drscmd
import cmod.fmt as fmt
import argparse
import logging  # Additional settings required

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

  session = ss.GUISession([cmdbase.wait, ss.shutdown])
  logger = logging.getLogger("SiPMCalibCMD.setup")
  prog_parser = argparse.ArgumentParser("control.py",
                                        "Starting an interactive CLI session",
                                        add_help=True,
                                        exit_on_error=True)
  prog_parser.add_argument('--init',
                           '-i',
                           type=str,
                           help="""File containing commands to run before the
                                handing the interactive session to the users""")
  args = prog_parser.parse_args()

  # Running the initialization script
  if args.init:
    try:
      session.cmd.onecmd(f'runfile {args.init}')
    except Exception as err:
      logger.error(
          f"Error initializing using file {args.init}. We will continue, but the command session may misbehave!"
      )

  session.start_session()  # Starting the session!
  # Notice that this will continue to run until the shutdown signal is sent from
  # a client side request.

  # Currently this seg-faults on exit. I am not sure which hardware interface is
  # not being released properly, but doesn't seem to cause any persistent issue
  # as far as I can tell.
  del session
