"""

gcodercmd.py

Commands related with direct controls of the gantry system (just the gcoder
controls). Due to legacy reasons, this will include the luminosity alignment
commands, as well as the non-linear scan command by moving in z.

"""
import ctlcmd.cmdbase as cmdbase
import numpy as np
from scipy.optimize import curve_fit
import time


class set_gcoder(cmdbase.controlcmd):
  """
  @brief Setting the gcoder device path.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('devpath',
                             type=str,
                             help="""
                             path for the gcoder. Should be something like
                             `/dev/tty<SOMETHING>`. You can explicitly set up
                             the dummy gcoder device by including "dummy" in
                             the device path.""")

  def run(self, args):
    """
    You can set up a dummy device by
    """
    if not args.devpath.startswith('/dev') or 'dummy' in dev:
      self.printwarn(f"""
        Path [{args.devpath}] for gcoder device is as dummy path, a dummy gcoder
        device will be used.""")
      self.init_dummy(args)
    else:
      try:
        self.gcoder.init(args.printerdev)
        printset = self.gcoder.getsettings()
        printset = printset.split('\necho:')
        self.devlog('GCoder').info('<br>'.join(printset))
      except RuntimeError as err:
        self.devlog('GCoder').error(str(err))
        self.printwarn(
            """Failed to setup printer, skipping over settings and setting
            coordinates to (0,0,0)""")
        self.init_dummy(args)
        self.move_gantry(0.1, 0.1, 0.1)

  def init_dummy(self, args):
    """Setting up the gcoder device as a dummy device."""
    pass  # Currently do nothing


class get_gcoder(cmdbase.controlcmd):
  """
  @brief Getting the device settings for the gcoder
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, args):
    logger = self.devlog("GCoder")
    level = fmt.logging.INT_INFO
    logger.log(level, 'device: ' + str(self.gcoder.dev_path))
    logger.log(
        level, f'current coordinates:' + ' x:{0:.1f} y:{1:.1f} z:{2:.1f}'.format(
            self.gcoder.opx, self.gcoder.opy, self.gcoder.opz))
    settings = self.gcoder.getsettings().split('\necho:')
    logging.log(level, '\n'.join(line))


class rungcode(cmdbase.controlcmd):
  """
  Running a raw command gcode command.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    """Adding the string argument"""
    self.parser.add_argument("cmd", type=str, help="Raw gcode command to run")
    self.parser.add_argument("--wait",
                             '-w',
                             type=int,
                             default=10_000,
                             help="Maximum time to wait for the command to end")

  def run(self, args):
    """
    @brief Running the gcode command

    @details While the wait time is set to 10000 seconds, this is not
    representative of a true wait time, as commands can return the 'ok' signal
    as soon as the internal state of the printer is modified, rather than when
    the command actually finishes execution.
    """
    retstr = self.gcoder.run_gcode(args.cmd, 0, int(1e5))
    retstr = retstr.split('\necho:')
    for line in retstr:
      self.printmsg(line, extra={'device': 'Printer'})


class moveto(cmdbase.singlexycmd):
  """
  Moving the gantry head to a specific location, either by det ID or by raw
  x,y,z coordinates.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-z',
                             type=float,
                             help="Specifying the z coordinate explicitly [mm].")

  def parse(self, args):
    if not args.z: args.z = self.gcoder.opz
    return args

  def run(self, args):
    self.move_gantry(args.x, args.y, args.z)


class disablestepper(cmdbase.controlcmd):
  """Manual disabling of stepper motor."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-x',
                             action='store_true',
                             help='Disable x axis stepper motors')
    self.parser.add_argument('-y',
                             action='store_true',
                             help='Disable y axis stepper motors')
    self.parser.add_argument('-z',
                             action='store_true',
                             help='Disable z axis stepper motors')

  def run(self, args):
    self.gcoder.disablestepper(args.x, args.y, args.z)


class enablestepper(cmdbase.controlcmd):
  """Manual re-enabling of stepper motor."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-x',
                             action='store_true',
                             help='Activate x axis stepper motors')
    self.parser.add_argument('-y',
                             action='store_true',
                             help='Activate y axis stepper motors')
    self.parser.add_argument('-z',
                             action='store_true',
                             help='Activate z axis stepper motors')

  def run(self, args):
    self.gcoder.enablestepper(args.x, args.y, args.z)


class movespeed(cmdbase.controlcmd):
  """Setting the motion speed of the gantry x-y-z motors. Units in mm/s."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-x',
                             type=float,
                             help='motion speed of gantry in x axis')
    self.parser.add_argument('-y',
                             type=float,
                             help='motion speed of gantry in y axis')
    self.parser.add_argument('-z',
                             type=float,
                             help='motion speed of gantry in z axis')

  def parse(self, args):
    if not args.x: args.x = float('nan')
    if not args.y: args.y = float('nan')
    if not args.z: args.z = float('nan')

    return args

  def run(self, args):
    self.gcoder.set_speed_limit(args.x, args.y, args.z)


class sendhome(cmdbase.controlcmd):
  """Sending the gantry system home and reset in the internal coordinate."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-x',
                             action='store_true',
                             help='reset x coordinates to 0')
    self.parser.add_argument('-y',
                             action='store_true',
                             help='reset y coordinates to 0')
    self.parser.add_argument('-z',
                             action='store_true',
                             help='reset z coordinates to 0')
    self.parser.add_argument('--all',
                             '-a',
                             action='store_true',
                             help='reset all coordinates to 0')

  def parse(self, args):
    # Filling with NAN for missing settings.
    if args.all:
      args.x = True
      args.y = True
      args.z = True
    return args

  def run(self, args):
    self.gcoder.sendhome(args.x, args.y, args.z)
