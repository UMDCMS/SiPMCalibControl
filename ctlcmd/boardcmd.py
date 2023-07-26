"""
  boardcmd.py

  Commands that are used for modifying the board and its conditions. 
  This includes loading and saving the coordinates calibration results.
"""

import ctlcmd.cmdbase as cmdbase
import cmod.fmt as fmt
import argparse

class save_board(cmdbase.controlcmd):
  """
  @brief Saving current board session.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--filename',
                             '-f',
                             type=str,
                             help="""
                             Overwrite the board configuration json filename to save current board session.""",
                             required=False)

  def run(self, args):
    """
    For the sake of clarity, device settings is split into each of their
    functions. Notice that all function should have exception guards so the
    subsequent settings can still be set if settings for one particular device
    is bad or not available.
    """
    try:
      if args.filename:
        self.board.save_board(args.filename)
      else:
        self.board.save_board()
    except RuntimeError as err:
      self.printerr(str(err))
      self.printwarn('Board saving has failed, skipping...')

class load_board(cmdbase.controlcmd):
  """
  @brief Loading board from given config filename.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--filename',
                             '-f',
                             type=str,
                             help="""
                             The board configuration json filename to load current board session.""",
                             required=True)

  def run(self, args):
    """
    For the sake of clarity, device settings is split into each of their
    functions. Notice that all function should have exception guards so the
    subsequent settings can still be set if settings for one particular device
    is bad or not available.
    """
    # add the board conditions
    if args.filename:
      if self.board.load_board(args.filename):
        self.printinfo(f"Board loaded from {args.filename.name}")
      else:
        self.printerr(f"Board loading from {args.filename.name} failed")