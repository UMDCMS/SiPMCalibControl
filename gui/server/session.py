"""
  session.py

  Defining the objects required for a GUI session. This includes includes the
  following parts:

  - A modified controlterm instance with it's logging instances modified.
  - The python.flask application instance.
  - The python.flask socketio instance.
  - A new logger instance used for slow data monitoring stream
  - A new logging handler to send data over socket io interface.

  Since actions using the flask and socket io instances are very verbose, the
  `Session` object will mainly act as a container class, with the implementation
  of flask.route and socketio.on methods split into the various for clarity.


"""
# from flask import Flask, request
# from flask_socketio import SocketIO
# from threading import Thread

# import views as views
# import sockets as sockets
import ctlcmd.cmdbase as cmdbase  # For the command line session
import cmod.fmt as fmt

## Additional python libraries
import os, logging, tqdm, datetime, time, trace, sys


class GUISocketHandler(logging.Handler):
  """
  GUI socketio handler to emit a message to all connect clients when a logging
  information arrives.
  """
  def __init__(self, socketio, level):
    super().__init__(level=level)
    self.socketio = socketio

  def emit(self, record):
    if 'GUIMonitor' in record.name:
      self.socketio.emit('monitor-info', record.__dict__)
    else:
      self.socketio.emit('logging-info', record.__dict__)


class GUIcontrolterm(cmdbase.controlterm):
  """
  @brief Overloading the logging functions and user input methods to allow for
  interactions through the web GUI
  """
  def __init__(self, cmdlist, session, **kwargs):
    """User action prompts requires a reference to the socketio interface"""
    self.session = session  # Required before the parent constructor
    super().__init__(cmdlist)

    # Overwriting the interupt signal handler to be used by command instances.
    self.sighandle = self.session.sighandle
    for cmd in cmdlist:
      cmdname = cmd.__name__.lower()
      cmdinst = getattr(self, cmdname)
      cmdinst.sighandle = self.sighandle

    self.session_lock_string = ''

     # add handler for whenever the board is changed or loaded
    self.board.set_update_handler(self.board_handler)

  def board_handler(self, board):
    """
    @brief Handler for whenever the board is changed or loaded

    @details This handler will be called whenever the board is loaded or
    changed. Here we will be updating the board instance in the session object
    to match the current board instance.
    """
    self.socketio.emit('board-update', board.__dict__())

  def init_log_format(self):
    """
    @brief Overloading the settings for the logger instances.

    @details Additional settings for the memory settings

    - An in-memory handler, which stores up to 65536 logging entries for the
      command line session. This is mainly used for history look up and
      debugging dump log. Here we will attempt to log everything.
    - An additional signal
    """
    self.mem_handle = self.session.mem_handle
    self.cmdlog.addHandler(self.session.mem_handle)
    self.cmdlog.addHandler(self.session.sock_handle)

  def prompt_input(self, device, message, allowed=None) -> str:
    """
    @brief Prompting for a user message, suspend the session until the input is
    placed.

    @details If the allowed entry is not None, then the input will need to be
    included in the allowed value, or the prompt will an error message will be
    pushed to the client.

    Here we are explicitly setting the session_lock_string to be some
    non-keyboard character, and we will wait until the session_lock_string has
    been modified by the user via some socket input. Here we are simply
    performing a dumb suspension routine by checking over 0.1 seconds for the
    string to be modified.
    """
    __DEFAULT_IMPOSSIBLE_STRING__ = '®®®®®®®®©©©©©©©'
    self.session_lock_string = __DEFAULT_IMPOSSIBLE_STRING__

    self.devlog(device).log(fmt.logging.CMD_HIST, message, 'request_input')
    # This message will be passed to the client session for parsing.
    while True:
      if self.sighandle.terminate:
        raise InterruptedError('Interupt signal received')
      # String has been modified.
      if self.session_lock_string != __DEFAULT_IMPOSSIBLE_STRING__:
        if allowed is not None and self.session_lock_string not in allowed:
          self.devlog(device).error(
              fmt.oneline_string(f"""Illegal value: {self.session_lock_string}
                                  valid inputs: {allowed}"""))
          self.session_lock_string = __DEFAULT_IMPOSSIBLE_STRING__
        else:
          return self.session_lock_string
      # Default behavior for no inputs.
      else:
        pass
      time.sleep(0.1)


class SocketTQDM(tqdm.cli.tqdm):
  """
  Custom tqdm object to allow the progress of a command running on the server
  side to be passed to the remote client. Since the tqdm instance required by
  the command objects needs to be initialized. with only objects recognized by
  the vanilla tdqm object, this object will not be directly used to override the
  progress bar constructor.
  """
  def __init__(self, socketio, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.socketio = socketio

  def update(self, n=1):
    """
    Changing the update to also emit a socket signal on the update progress.
    """
    super().update(n)
    self.socketio.emit(
        'progress-update', {
            k: v
            for k, v in self.__dict__.items()
            if k in ['desc', 'total', 'n', 'postfix']
        })


class GUIsignalhandle(object):
  """
  As we will not be intercepting server side SIGTERM signals. Here we simple
  have an object that is identical to the controlsignalhandle except we don't
  attempt to overload the raw signal handling function, as 'interrupt signals'
  will just be some message sent from the client.
  """
  def __init__(self):
    self.terminate = False

  def reset(self):
    self.terminate = False

  def release(self):
    self.terminate = False


class TraceThread(Thread):
  """
  Thread with additional trace injected to allow for termination. Solution taken
  from https://www.geeksforgeeks.org/python-different-ways-to-kill-a-thread/
  """
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.terminate_flag = False

  def start(self):
    self.__run_backup = self.run
    self.run = self.__run
    super().start()

  def __run(self):
    sys.settrace(self.globaltrace)
    self.__run_backup()
    self.run = self.__run_backup

  def globaltrace(self, frame, event, arg):
    if event == 'call':
      return self.localtrace
    else:
      return None

  def localtrace(self, frame, event, arg):
    if self.terminate_flag:
      if event == 'line':
        raise SystemExit()
    return self.localtrace

  def terminate(self):
    self.terminate_flag = True


class GUISession(object):
  """
  Session object that contains all of the session parameters. Since a bunch of
  the manipulation of the data member is heavily tied with the calibration
  processes, this fill will only contain a list the data members. The actual
  manipulation of the data members will be written in the action.py file behind
  the calibration part.

  In addition, so pass the full functionality of the underlying cmd class to the
  GUI terminal, we will be using the following file descriptors to interact with
  the cmd class. Two descriptors will be opened for each of the file input output
  sessions as reading and writing will need two different descriptor values. For
  the sake of having semi-serviceable terminal interactions, a string buffer and
  buffer index is also used to keep track of the current line.

  This class is strictly a container class, with minimal amounts of data
  manipulation. All manipulations of the global container instance 'session' is
  handled by the various function methods in the .py files.
  """

  # Static variable for session state values
  STATE_IDLE = 0
  STATE_RUNNING = 1

  def __init__(self, cmdlist):
    self.state = GUISession.STATE_IDLE
    # Creating the flask instance:
    self.app = Flask("SiPMCalibGUI",
                     template_folder=os.path.dirname(__file__) + '/templates',
                     static_folder=os.path.dirname(__file__),
                     static_url_path=os.path.dirname(__file__))
    self.socketio = SocketIO(self.app,
                             debug=False,
                             async_mode='threading',
                             logger=False,
                             cors_allowed_origins='*')

    # Additional initialization routines
    self.__init_log_handlers__()
    # self.__init_flask__()
    self.__init_socketio__()
    self.__init_calibration_defaults__()

    # Needs to be created after everything else
    self.is_running = False  # Flag to hard lock incoming requests
    self.sighandle = GUIsignalhandle()
    self.cmd = GUIcontrolterm(cmdlist, self)

    # Custom function for making the various objects
    def _MAKE_CUSTOM_TQDM_(*args, **kwargs):
      return SocketTQDM(self.socketio, *args, **kwargs)

    cmdbase.controlcmd._PROGRESS_BAR_CONSTRUCTOR_ = _MAKE_CUSTOM_TQDM_

  def __init_log_handlers__(self):
    """
    @brief Initializing the logging handlers

    @details settings as top level object so that all objects required to run
    the GUI session can get access to these regardless and we don't need to keep
    track of which object it was declared in. Here we consider 3 handlers

    - An in-memory handler for the command session
    - An in-memory handler for the monitoring stream (temperature and gantry
      configuration position)
    - A socket handler to emit signals to all connect clients when log entry is
      emitted.
    """
    # Setting up a "main" logging of server side logs (like command parsing
    # exceptions.)
    self.logger = fmt.logging.getLogger('SiPMCalibCMD.GUIserver')

    # For session state monitoring logging (like session state changes and
    # temperature) here we are using a separate logger to ensure that the
    # monitor information does not wipe out slow information.
    self.mon_log = fmt.logging.getLogger('GUIMonitor')

    # Additional handlers to be used by the various systems.
    self.mem_handle = fmt.FIFOHandler(65536, level=logging.NOTSET)
    self.mon_handle = fmt.FIFOHandler(65536, level=logging.NOTSET)
    self.sock_handle = GUISocketHandler(self.socketio, level=logging.NOTSET)

    # Setting up the handlers (the self.logger is set up by the controlterm
    # object.)
    self.mon_log.addHandler(self.mon_handle)
    self.mon_log.addHandler(self.sock_handle)

  # def __init_flask__(self):
  #   """
  #   @brief Setting up the application URL response methods.

  #   @details Implementation of these methods can be found in the views.py file.
  #   Here we add a thin wrapper so that the session instance can be used by the
  #   view function instances.
  #   """
  #   # Forcing a debug server for easier handling of server shutdown (This )
  #   self.app.debug = True
  #   for url, vfunc in [
  #       ('/', 'index'),  #
  #       ('/devicesettings', 'device_settings'),
  #       ('/geometry/<boardtype>', 'geometry'),  #
  #       ('/report/<reporttype>', 'status'),  #
  #       ('/databyfile/<process>/<filename>', 'databyfile'),  #
  #       # ('/databyprocess/<process>/<detid>', 'databyprocess'),  #
  #       ('/visual', 'visual'),  #
  #       ('/logdump/<logtype>', 'logdump'),  #
  #   ]:
  #     setattr(self, f'view_{vfunc}', getattr(views, vfunc)(self))
  #     self.app.add_url_rule(url,
  #                           endpoint=url,
  #                           view_func=getattr(self, f'view_{vfunc}').__call__)

  def __init_socketio__(self):
    """
    @brief Setting up the actions to be executed on the socket event

    @details Implementation of these methods can be found in the socket.py file.
    Here we add a thin wrapper so that the session instance cane be used by the
    socket function instances.
    """
    socket_lookup = [('connect', 'socket_connect'),  #
                     ('run-single-cmd', 'run_single_cmd'),  #
                     ('interrupt', 'interrupt'),
                     ('user-action-check', 'prompt_check')]
    for event, sfunc in socket_lookup:
      setattr(self, f'socket_{sfunc}', getattr(sockets, sfunc)(self))
      self.socketio.on_event(event, getattr(self, f'socket_{sfunc}').__call__)
      

  def __init_calibration_defaults__(self):
    ## Stuff related to the generation of standard commands
    self.zscan_samples = 100
    self.zscan_zlist_sparse = [10, 15, 20, 50]
    self.zscan_zlist_dense = [10, 12, 14, 16, 18, 20, 30]
    self.zscan_power_list = [0.1, 0.5, 0.8, 1.0]

    self.lowlight_samples = 1000
    self.lowlight_pwm = 0.5
    self.lowlight_zval = 30

    self.lumialign_zval = 10
    self.lumialign_pwm = 0.5
    self.lumialign_range = 6
    self.lumialign_distance = 2
    self.lumialign_samples = 100

    self.visual_zval = 5

  def run_command(self, cmd):
    """
    Running a single command. Here we will need to run the pre/one/post pattern
    defined in the controlterm instance explicitly, we will also return the
    execution status.
    """
    cmd = self.cmd.precmd(cmd)
    sig = self.cmd.onecmd(cmd)
    return self.cmd.postcmd(sig, cmd)

  def update_session_state(self, new_state):
    """
    Updating the session state (from running to keeping no-running or vice
    versa), this transition should always be logged and passed to any connected
    client.
    """
    self.state = new_state
    self.mon_log.log(
        fmt.logging.MONITOR,
        '',
        extra={
            'state':
            self.state,
            'pulser_temp':
            self.cmd.gpio.ntc_read(0),
            'sipm_temp':
            self.cmd.gpio.rtd_read(1),
            'pulser_lv':
            self.cmd.gpio.adc_read(2),
            'gantry_coord':
            (self.cmd.gcoder.cx, self.cmd.gcoder.cy, self.cmd.gcoder.cz)
        })

  def error(self, msg):
    """Short hand for making session error message"""
    self.logger.error(fmt.oneline_string(msg))

  def warning(self, msg):
    """Short hand for making session warning message"""
    self.logger.warning(fmt.oneline_string(msg))

  def info(self, msg):
    """Short hand for making session info message"""
    self.logger.info(fmt.oneline_string(msg))

  def start_session(self):
    self.is_serving = True

    def monitor_loop():  # Thin wrapper to create a continuous update
      while self.is_serving:
        self.update_session_state(self.state)
        time.sleep(0.5)

    self.is_serving = True
    self.monitor_thread = Thread(target=monitor_loop)
    self.monitor_thread.start()
    self.socketio_thread = TraceThread(target=self.socketio.run,
                                       args=(self.app, ),
                                       kwargs=dict(host='0.0.0.0',
                                                   port=9100,
                                                   debug=False))
    self.socketio_thread.start()

    print('Monitor thread status:', self.monitor_thread.is_alive())

  def stop_session(self):
    self.is_serving = False
    self.socketio.emit('server-shutdown')
    # Stopping the thread with a terminate signal
    self.monitor_thread.join()  # Waiting for the monitoring thread to stop.
    self.socketio_thread.terminate()
    self.socketio_thread.join()


class shutdown(cmdbase.controlcmd):
  """
  Shutting down the server session. We will prompt the user for inputs before
  starting the shutdown routine, only the message prompting will be defined in
  this class, all other operations should be handled by the
  GUIsession.stop_session method.
  """
  def __init__(self, cmd):
    super().__init__(cmd)

  def run(self, args):
    self.prompt_input(fmt.oneline_string("""
        You have initiated the routine to terminate the server session!

        <ul>

        <li>If you are sure you want to shutdown, plase enter "I am sure, stop
        the server" into the input box below to complete the shutdown, the
        browser should refresh to a blank page shortly after entering. </li>

        <li>If you want to continue the session, hit the interrupt signal
        button. An error would be kept in the log</li>

        </ul>
    """),
                      allowed=['I am sure, stop the server'])
    self.cmd.session.stop_session()
