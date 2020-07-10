from flask import Flask, render_template, Response
from flask_socketio import SocketIO
import datetime
import logging ## System logging that is used by the application

## Command interface
import ctlcmd.cmdbase as cmdbase
import ctlcmd.motioncmd as motioncmd
import ctlcmd.getset as getset
import ctlcmd.digicmd as digicmd
import ctlcmd.viscmd as viscmd
import ctlcmd.picocmd as picocmd
import cmod.logger as logger
import sys
import copy
import io


socketio = SocketIO(debug=False, async_mode='threading',)
#cors_allow_origins='*' )

from .sockets import session
from .sockets.parsing import *

def create_server_flask(debug=False):
  """
  Generating the server instance, keeping the app instance as a member of the
  global socketio object so other members can use this.
  """
  socketio.app = Flask(__name__)
  socketio.app.debug = debug

  # Since this is a single paged document
  @socketio.app.route('/')
  def index():
    return render_template('index.html')

  @socketio.app.route('/video_monitor')
  def video_monitor():
    return Response(
        GetCurrentImage(), # (unfortunately) defined in the parsing.py file
        mimetype='multipart/x-mixed-replace; boundary=frame' )

  @socketio.app.route('/visual_cache/<detid>')
  def get_det_image(detid):
    return Response(
      GetDetectorImage(detid), # This is also in parsing.py file
      mimetype='multipart/x-mixed-replace; boundary=frame' )


  @socketio.on('connect', namespace='/sessionsocket')
  def monitor_connect():
    print('Monitor client connected')
    SocketConnect(socketio)

  @socketio.on('get-report', namespace='/sessionsocket')
  def get_system_configuration(msg):
    RunReport(socketio, msg)

  @socketio.on('run-action-cmd', namespace='/sessionsocket')
  def run_action(msg):
    RunAction(socketio, msg)

  @socketio.on('complete-user-action', namespace='/sessionsocket')
  def complete_user_action(msg):
    CompleteUserAction(socketio)

  ## Resetting the socket application stuff
  socketio.init_app(socketio.app)

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
      '--camdev': '/dev/video0',
      #'-boardtype': 'cfg/static_calib.json',
      '--action': 'cfg/useractions.json',
      '--picodevice': 'MYSERIAL',  #Cannot actually set. Just dummy for now
      #'-remotehost' : ['hepcms.umd.edu', '']
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
    logger.printwarn(
        'There was error in the setup process, program will '
        'continue but will most likely misbehave! Use at your own risk!')

  return socketio.app
