"""
  gantrycmd.py

  Commands that are used for saving and loading the gantry conditions.
"""

import ctlcmd.cmdbase as cmdbase
import cmod.fmt as fmt
import argparse

class save_gantry_conditions(cmdbase.controlcmd):
  """
  @brief Saving current session gantry conditions.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--filename',
                             '-f',
                             type=str,
                             help="""
                             Overwrite the filename to save current session gantry conditions in.""",
                             required=False)

  def run(self, args):
    # add the board conditions
    try:
      if args.filename:
        self.conditions.save_gantry_conditions(args.filename)
      else:
        self.conditions.save_gantry_conditions()
      self.printmsg(f"Gantry conditions successfully saved to {args.filename}.")
    except RuntimeError as err:
      self.printerr(str(err))
      self.printwarn(f'Saving gantry conditions to {args.filename} has failed.')

class load_gantry_conditions(cmdbase.controlcmd):
  """
  @brief Loading gantry conditions from given filename.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--filename',
                             '-f',
                             type=str,
                             help="""
                             The json file name to load gantry conditions from.""",
                             required=True)

  def run(self, args):
    if args.filename:
      if self.conditions.load_gantry_conditions(args.filename):
        self.printmsq(f"Gantry conditions loaded from {args.filename}")
      else:
        self.printerr(f"Gantry conditions loading from {args.filename} failed")