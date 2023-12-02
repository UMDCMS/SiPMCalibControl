"""

sockets.py

Server-side actions to take on receiving socket signal. There are 2 types
expected in the server-client interaction:

- The client is request some sort of an action to be performed by the server
  session, in which case, the server session will first check that it isn't
  already running something, then locks the server session with the "running
  state" flag, executes the action request, and finally releasing the system.

- The client is passing one-time information to the server. These should be
  processed by the server session regardless of session state.

For this the SocketFunction is used to allow a short hand to the main server
session instance to be accessible to all classes handling the socket signals,
this class is sufficient for the second type of signal processing. An additional
`ActionRequest` abstract class further overloads the __call__ method to handle
the state checking and locking routine.
"""

import session as ss
import cmod.fmt as fmt


class SocketFunction(object):
  """
  Generic function object to be handled to socket signal requests, the signal
  will always have access to the session instance as a short hand.
  """
  def __init__(self, session):
    self.session = session
    self.socketio = session.socketio  # Short hand for socket instance

  def __call__(self, msg):
    """Method to be overloaded for the socket signal processing"""
    pass


class ActionRequest(SocketFunction):
  """
  These are actions requests that need the server session to be free before
  processing. Here we fixe the __call__ method to handle the parsing of session
  state and exception handling. Subsequent classes should overload the execute
  method.
  """
  def __call__(self, msg):
    if self.session.state is ss.GUISession.STATE_RUNNING:
      self.session.error("""Receive request when the system was already busy,
                         ignoring this new request.""")
      return
    else:
      try:
        self.session.update_session_state(ss.GUISession.STATE_RUNNING)
        self.execute(msg)
      except Exception as err:
        # Catch the exception and pass it on to the client side for display
        self.session.error(str(err))
      finally:
        self.session.update_session_state(ss.GUISession.STATE_IDLE)

  def execute(self, msg):
    """Method to be overloaded by subsequent classes"""
    pass


class socket_connect(SocketFunction):
  """
  What to do on socketio connection establishment:

  - Add an info entry to the log.
  """
  def __call__(self, msg):
    self.session.info('Server received new connection from client!')


class run_single_cmd(ActionRequest):
  """Executing a single command send from the session"""
  def execute(self, msg):
    if msg:  # Only execute non-empty strings
      self.session.run_command(msg)


class interrupt(SocketFunction):
  """
  Receiving an interruption signal, the commands in the underlying command-line
  session will handled the termination of the running process gracefully.
  """
  def __call__(self, msg):
    self.session.sighandle.terminate = True
    #send_interrupt(socketio)


class prompt_check(SocketFunction):
  """
  Receiving the string used to unlock a prompt section. Notice that the session
  should be able to receive when the session is 'running', as this is usually use
  in the wait command or for user input prompts (Hence a vanilla SocketFunction
  rather than an ActionRequest). Here we simply pass the string to the
  session_lock_string of the command line session, and the command line with be
  responsible for further processing and releasing the session if the message
  passes the requirement.
  """
  def __call__(self, msg):
    self.session.cmd.session_lock_string = msg
