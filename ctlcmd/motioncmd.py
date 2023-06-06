"""

motioncmd.py

Commands related with controlling the gantry motion. Due to legacy reasons,
this will include the luminosity alignment commands, as well as the non-linear
scan command by moving in z.

"""
import ctlcmd.cmdbase as cmdbase
import numpy as np
from scipy.optimize import curve_fit
import time


class rungcode(cmdbase.controlcmd):
  """
  Running a raw command gcode command.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    """Adding the string argument"""
    self.parser.add_argument("cmd", type=str, help="Raw gcode command to run")

  def parse(self, args):
    """Adding the end-of-line character to the command string (used by GCoder)"""
    args.cmd = args.cmd + '\n'
    return args

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


class getcoord(cmdbase.controlcmd):
  """Printing current gantry coordinates"""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, args):
    self.printmsg('x:{0:.1f} y:{1:.1f} z:{2:.1f}'.format(
        self.gcoder.cx, self.gcoder.cy, self.gcoder.cz))


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


class halign(cmdbase.readoutcmd, cmdbase.hscancmd, cmdbase.savefilecmd):
  """
  @brief Running horizontal alignment procedure by luminosity readout vs and xy
  grid scan motion.
  """

  DEFAULT_SAVEFILE = 'halign_<BOARDTYPE>_<BOARDID>_<DETID>_<SCANZ>_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    """
    @brief Adding the overwrite and power settings
    """
    self.parser.add_argument('--overwrite',
                             action='store_true',
                             help="""Forcing the storage of scan results as
                             session information""")
    self.parser.add_argument('--power',
                             '-p',
                             type=float,
                             help="""The PWM duty cycle to set the pulser board
                             during the luminosity scan.""")

  def parse(self, args):
    """Only additional parsing is checking the power option."""
    if args.power == None:
      args.power = self.gpio.pwm_duty(0)
    return args

  def run(self, args):
    """
    @details The command routine is as followed:
    - Given the list of parsed coordinates in the arguments, we loop over the
      coordinates and take a luminosity measurement at each of the coordinate.
      Results are aggregated into a and array, and a measurement result is
      listed for each measurement performed in the output save file.
    - The results is fitted to the inverse square model, the initial fit
      results is estimated with the center coordinates taken to be the
      estimated luminosity center.
    - Fitting results is either saved to the calibration cache, or is prompted
      to be saved, depending on the current state of the calibration.
    """
    self.gpio.pwm(0, args.power, 1e5)
    lumi = []
    unc = []
    total = len(args.x)

    ## Running over mesh.
    for xval, yval in self.start_pbar(zip(args.x, args.y)):
      self.check_handle()
      self.move_gantry(xval, yval, args.scanz)
      lumival, uncval = self.readout(args, average=True)
      self.write_standard_line((lumival, uncval), det_id=args.detid)
      self.pbar_data(Lumi=f'{lumival:.2f}+-{uncval:.2f}')
      lumi.append(abs(lumival))
      unc.append(uncval)

    # Performing fit
    p0 = (
        max(lumi) * ((args.scanz + 2)**2),  #
        np.mean(args.x),  #
        np.mean(args.y),  #
        args.scanz,  #
        min(lumi))
    try:
      fitval, fitcovar = curve_fit(halign.model,
                                   np.vstack((args.x, args.y)),
                                   lumi,
                                   p0=p0,
                                   sigma=unc,
                                   maxfev=1000000)
    except Exception as err:
      self.printerr(f"""
                    Lumi fit failed to converge, check output stored in file
                    {self.savefile.name} for collected values""")
      self.move_gantry(args.x, args.y, args.scanz)
      raise err

    def meas_str(v, u):
      return f'{v:.1f}+-{u:.2f}'

    self.printmsg(f'Best x:' + meas_str(fitval[1], np.sqrt(fitcovar[1][1])))
    self.printmsg(f'Best y:' + meas_str(fitval[2], np.sqrt(fitcovar[2][2])))
    self.printmsg(f'Fit  z:' + meas_str(fitval[3], np.sqrt(fitcovar[3][3])))

    detid = str(args.detid)  ## Ensuring string convention in using this
    ## Generating calibration det id if using det coordinates
    if not detid in self.board.dets() and int(detid) < 0:
      self.board.add_calib_det(detid, args.mode, args.channel)

    ## Saving session information
    if not self.board.lumi_coord_hasz(detid, args.scanz) or args.overwrite:
      self.board.add_lumi_coord(detid, args.scanz, [
          fitval[1],
          np.sqrt(fitcovar[1][1]), fitval[2],
          np.sqrt(fitcovar[1][1])
      ])
    elif self.board.lumi_coord_hasz(detid, args.scanz):
      if self.prompt_yn(f"""A lumi alignment for z={args.scanz:.1f} already
                        exists for the current session, overwrite?""",
                        default=False):
        self.board.add_lumi_coord(detid, args.scanz, [
            fitval[1],
            np.sqrt(fitcovar[1][1]), fitval[2],
            np.sqrt(fitcovar[1][1])
        ])

    ## Sending gantry to position
    if (fitval[1] > 0 and fitval[1] < self.gcoder.max_x() and fitval[2] > 0
        and fitval[2] < self.gcoder.max_y()):
      self.move_gantry(fitval[1], fitval[2], args.scanz)
    else:
      self.printwarn("""Fit position is out of gantry bounds, the gantry will not
      attempt to move there""")

  @staticmethod
  def model(xydata, N, x0, y0, z, p):
    """Inverse square model used for fitting"""
    x, y = xydata
    D = (x - x0)**2 + (y - y0)**2 + z**2
    return (N * z / D**1.5) + p


class zscan(cmdbase.singlexycmd, cmdbase.zscancmd, cmdbase.readoutcmd,
            cmdbase.savefilecmd):
  """
  Performing the intensity scan give a list of scanning z coordinates and the
  list of biassing power.
  """

  DEFAULT_SAVEFILE = 'zscan_<BOARDTYPE>_<BOARDID>_<DETID>_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    """Adding the power settings (accepts list)"""
    self.parser.add_argument('--power',
                             '-p',
                             nargs='*',
                             type=float,
                             help="""Give a list of pwm duty cycle values to
                             try for each coordinate point""")

  def parse(self, args):
    """Setting power list to current value if it doesn't exist"""
    if not args.power:
      args.power = [self.gpio.pwm_duty(0)]  ## Getting the PWM value
    return args

  def run(self, args):
    """
    @details For each of the z values and PWM power value listed in the
    arguments, we move the gantry over to the cooridnates, set the PWM
    settings, and take a measurement. The measurement is then saved to the
    standard data format. As there are no fitting done here, the command simply
    exists once all data collection is complete.
    """
    lumi = []
    unc = []

    # Ordering is important! Grouping z values together as the bottle neck is in
    # motion speed
    for z, power in self.start_pbar(
        [(z, p) for z in args.zlist for p in args.power]):
      self.check_handle()
      self.move_gantry(args.x, args.y, z)
      self.gpio.pwm(0, power, 1e5)  # Maximum PWM frequency

      lumival = 0
      uncval = 0
      while 1:
        lumival, uncval = self.readout(args, average=True)
        if args.mode == cmdbase.readoutcmd.Mode.MODE_PICO:
          wmax = self.pico.waveformmax(args.channel)
          current_range = self.pico.rangeA() if args.channel == 0 \
                          else self.pico.rangeB()
          if wmax < 100 and current_range > self.pico.rangemin():
            self.pico.setrange(args.channel, current_range - 1)
          elif wmax > 200 and current_range < self.pico.rangemax():
            self.pico.setrange(args.channel, current_range + 1)
          else:
            break
        else:
          break

      lumi.append(lumival)
      unc.append(uncval)

      self.fillroot(lumival,uncval)
      ##self.write_standard_line((lumival, uncval), det_id=args.detid)
      self.pbar_data(Lumi=f'{lumival:.2f}+-{uncval:.2f}')


class lowlightcollect(cmdbase.singlexycmd, cmdbase.readoutcmd,
                      cmdbase.savefilecmd):
  """@brief Collection of low light data at a single gantry position, data will
  be collected without averaging."""

  DEFAULT_SAVEFILE = 'lowlight_<BOARDTYPE>_<BOARDID>_<DETID>_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    """@brief adding the additional arguments"""
    self.parser.add_argument('-z',
                             type=float,
                             default=300,
                             help="""z height to perform the low light
                             collection result. (units: mm)""")
    self.parser.add_argument('--power',
                             '-p',
                             type=float,
                             help="""PWM duty cycle for data collection, using
                             current value if not specified""")

  def parse(self, args):
    """
    @details As the number of samples passed to the readoutcmd class is typically
    very large for the readout settings. Here we split the samples into segments
    of 1000 data collections as this will help to monitor and segment the
    function in-case of user cutoff.
    """
    if not args.power:
      args.power = self.gpio.pwm_duty(0)
    ## Modifying the sample argument to make monitoring simpler:
    args.nparts = (args.samples // 1000) + 1
    args.samples = 1000
    return args

  def run(self, args):
    """
    @brief Running low light collection.

    @details Operation of this command relatively straight forwards, simply run
    the readout command multiple times with no averaging and write to a file in
    standard format. Progress will be printed for every 1000 data collections.
    """
    self.move_gantry(args.x, args.y, args.z)
    self.gpio.pwm(0, args.power, 1e5)
    for _ in self.start_pbar(range(args.nparts)):
      self.check_handle()
      readout = self.readout(args, average=False)
      self.write_standard_line(readout, det_id=args.detid)
      self.pbar_data(Lumi=f'{readout[-1]:.2}')


class timescan(cmdbase.readoutcmd, cmdbase.savefilecmd):
  """
  Generate a log of the readout in terms relative to time.
  """
  DEFAULT_SAVEFILE = 'tscan_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--nslice',
                             type=int,
                             default=30,
                             help='total number of measurement to take')
    self.parser.add_argument('--interval',
                             type=float,
                             default=1,
                             help='Time interval between measurements (seconds)')
    self.parser.add_argument('--testpwm',
                             type=float,
                             nargs='*',
                             help="""PWM duty cycle values to cycle through
                             while performing test""")
    self.parser.add_argument('--pwmslices',
                             type=int,
                             default=10,
                             help="""Number of time slices to take for a given
                             PWM test value""")

  def parse(self, args):
    if not args.testpwm:
      args.testpwm = [self.gpio.pwm_duty(0)]
    return args

  def run(self, args):
    start_time = time.time_ns()
    pwmindex = 0

    for it in self.start_pbar(args.nslice):
      self.check_handle()
      if (it % args.pwmslices == 0):
        self.gpio.pwm(0, args.testpwm[pwmindex], 1e5)
        pwmindex = (pwmindex + 1) % len(args.testpwm)

      lumival, uncval = self.readout(args, average=True)
      s2 = self.visual.get_latest().s2
      s4 = self.visual.get_latest().s4
      sample_time = time.time_ns()
      timestamp = (sample_time - start_time) / 1e9
      self.write_standard_line((lumival, uncval, s2, s4),
                               det_id=-100,
                               time=timestamp)
      self.pbar_data(Lumi=f'{lumival:.2f}+-{uncval:.2f}',
                     Sharp=f'({s2:.1f}, {s4:.1f})')
      time.sleep(args.interval)
