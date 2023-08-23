"""
Defining show the socket io/Flask app instance is initialized, how client side
defined (AJAX) URLs should be processes and a simple wrapper for the parsing of
socket signals should be processes. For more detailed documentation of how
signals will be processes, see the documentation in the [sockets](sockets)
directory.
"""

import datetime
import logging  ## System logging that is used by the application
import threading

## Command interface
import ctlcmd.cmdbase as cmdbase
import ctlcmd.motioncmd as motioncmd
import ctlcmd.getset as getset
import ctlcmd.digicmd as digicmd
import ctlcmd.viscmd as viscmd
import ctlcmd.picocmd as picocmd
import sys, copy, io, json, os, re

##
# Right now only the threading async mode works without addition settings. This
# is not ideal.

from .sockets import session
from .sockets.parsing import *


def create_server_flask(debug=False):
  """
  Generating the server instance, keeping the app instance as a member of the
  global socketio object so other members can use this.
  """
  socketio.app = Flask(__name__)
  socketio.app.debug = debug

  ###############################################################################
  """
  Socket session processing. All processing functions are defined in parsing.py
  """
  ###############################################################################

  @socketio.on('resend', namespace='/sessionsocket')
  def resend(msg):
    resend_sync(socketio, msg)

  @socketio.on('run-action', namespace='/sessionsocket')
  def run_action_cmd_socket(msg):
    run_action(socketio, msg)

  @socketio.on('complete-user-action', namespace='/sessionsocket')
  def complete_user_action_socket(msg):
    complete_user_action(socketio)

  @socketio.on('interrupt', namespace='/sessionsocket')
  def interrupt():
    send_interrupt(socketio)

  ###############################################################################
  """
  Initialization of the underlying command line instance.
  """
  ###############################################################################

  # Duplicating the session to allow for default override.
  prog_parser = copy.deepcopy(session.cmd.set.parser)
  # Augmenting help messages
  prog_parser.prog = "gui_control.py"
  prog_parser.add_argument('-h',
                           '--help',
                           action='store_true',
                           help='print help message and exit')

  ## Using map to store Default values:
  default_overide = {
      '--printerdev': '/dev/ttyUSB0',
      #'--camdev': '/dev/video0',
      #'-boardtype': 'cfg/static_calib.json',
      '--drsdevice': "MYDRS",  # CANNOT actually set
      '--picodevice': 'MYSERIAL',  #Cannot actually set. Just dummy for now
  }

  for action in prog_parser._actions:
    for option, default in default_overide.items():
      if option in action.option_strings:
        action.default = default

  args = prog_parser.parse_args()

  if args.help:
    prog_parser.print_help()
    sys.exit(0)
  try:
    session.cmd.set.run(args)
    session.cmd.gpio.init()
  except Exception as err:
    logger.printerr(str(err))
    logger.printwarn("""
      There was error in the setup process, program will continue but will most
      likely misbehave! Use at your own risk!
      """)

  return socketio.app
