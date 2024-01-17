#!/usr/bin/env python3

# Loading the base class
import ctlcmd.cmdbase as cmdbase

# Getting the various functions
import ctlcmd.gcodercmd as gcodercmd
import ctlcmd.digicmd as digicmd
import ctlcmd.visualcmd as visualcmd
import ctlcmd.picocmd as picocmd
import ctlcmd.drscmd as drscmd
import ctlcmd.tbcmd as tbcmd
import ctlcmd.boardcmd as boardcmd
import ctlcmd.gantrycmd as gantrycmd
import ctlcmd.analysiscmd as analysiscmd

import cmod.fmt as fmt
import logging
import argparse

if __name__ == '__main__':
  # Setting the base logger to keep everything
  logging.root.setLevel(logging.NOTSET)

  # Declaring the list of commands that can be used
  cmd = cmdbase.controlterm([
      ## Direct interaction commands
      cmdbase.exit,  #
      cmdbase.history,  #
      cmdbase.logdump,  #
      cmdbase.wait,  #
      cmdbase.runfile,  #
      ## Gcoder control commands
      gcodercmd.set_gcoder,  #
      gcodercmd.get_gcoder,  #
      gcodercmd.rungcode,  #
      gcodercmd.moveto,  #
      gcodercmd.movespeed,  #
      gcodercmd.enablestepper,  #
      gcodercmd.disablestepper,  #
      gcodercmd.sendhome,  #
      ## Visual system controlling commands
      visualcmd.set_visual,  #
      visualcmd.get_visual,  #
      visualcmd.visualsaveframe,  #
      visualcmd.visualshowdet,  #
      ## Conditions saving and loading commands
      boardcmd.save_board,  #
      boardcmd.load_board,  #
      gantrycmd.save_gantry_conditions,  #
      gantrycmd.load_gantry_conditions,  #
      digicmd.pulse,  #
      digicmd.pwm,  #
      digicmd.setadcref,  #
      digicmd.showadc,  #
      digicmd.lighton,  #
      digicmd.lightoff,  #
      ## Pico setting commands
      picocmd.set_pico,  #
      picocmd.get_pico,  #
      picocmd.picorunblock,  #
      picocmd.picorange,  #
      drscmd.set_drs,  #
      drscmd.get_drs,  #
      drscmd.drscalib,  #
      drscmd.drsrun,  #
      # Tileboard interaction commands
      tbcmd.tbset,  #
      tbcmd.tb_saveconfig,  #
      tbcmd.tb_levelped,  #
      tbcmd.tb_test,

      # Analysis level commands that requires cross interaction across multiple
      # systems.
      analysiscmd.halign,  #
      analysiscmd.zscan,  #
      analysiscmd.lowlightcollect,  #
      analysiscmd.timescan,  #
      analysiscmd.visualhscan,  #
      analysiscmd.visualzscan,  #
      analysiscmd.visualmaxsharp,  #
      analysiscmd.visualcenterdet,  #
  ])
  #
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
      cmd.onecmd(f'runfile {args.init}')
    except Exception as err:
      logger.error(
          f"Error initializing using file {args.init}. We will continue, but the command session may misbehave!"
      )

  # Load the gantry conditions if any are uploaded
  try:
    filename = cmd.conditions.get_latest_gantry_conditions_filename()
    if filename is not None:
      # if so, then load the conditions from the file
      if cmd.conditions.load_gantry_conditions(filename):
        logger.info(f"Gantry conditions loaded from {filename}.")
      else:
        logger.error(f"Gantry conditions loading from {filename} failed.")
  except FileNotFoundError as err:
    logger.error(str(err))
    logger.warning(
        fmt.oneline_string("""
            There was error in loading the gantry conditions file, program will
            continue but will most likely misbehave! Use at your own risk!"""))

  # Starting the command loop
  cmd.cmdloop()
  del cmd  # This object requires explicit closing!
