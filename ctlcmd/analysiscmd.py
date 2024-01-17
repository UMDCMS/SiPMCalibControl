"""

analysiscmd.py

Analysis level command.

"""
import ctlcmd.cmdbase as cmdbase
import numpy as np
from scipy.optimize import curve_fit
import time


class halign(cmdbase.readoutcmd, cmdbase.hscancmd, cmdbase.rootfilecmd):
  """
  @brief Running horizontal alignment procedure by luminosity readout vs and xy
  grid scan motion.
  """

  DEFAULT_ROOTFILE = 'halign_<BOARDTYPE>_<BOARDID>_<DETID>_<SCANZ>_<TIMESTAMP>.root'

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
      self.printwarn('in halign parse')
      args.power = self.gpio.pwm_duty(0)
      self.printwarn('after halign power asign')
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

    n = 0
    test1 = []
    test2 = []
    ## Running over mesh.
    for xval, yval in self.start_pbar(zip(args.x, args.y)):
      self.check_handle()
      self.move_gantry(xval, yval, args.scanz)
      lumival, uncval = self.readout(args, average=True)
      self.fillroot({"lumival": lumival, "uncval": uncval}, det_id=args.detid)
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

    detid = int(args.detid)  ## Ensuring int convention in using this

    ## Saving session information
    coords = [
        fitval[1],
        np.sqrt(fitcovar[1][1]), fitval[2],
        np.sqrt(fitcovar[1][1])
    ]
    if not self.board.lumi_coord_hasz(detid, args.scanz) or args.overwrite:
      self.board.add_lumi_coord(detid, args.scanz, coords)
      self.conditions.update_gantry_and_sipm_conditions(self.classname, detid,
                                                        args.scanz)
    elif self.board.lumi_coord_hasz(detid, args.scanz):
      if self.prompt_yn(f"""A lumi alignment for z={args.scanz:.1f} already
                        exists for the current session, overwrite?""",
                        default=False):
        self.board.add_lumi_coord(detid, args.scanz, coords)
        self.conditions.update_gantry_and_sipm_conditions(
            'halign', detid, args.scanz)

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
            cmdbase.rootfilecmd):
  """
  Performing the intensity scan give a list of scanning z coordinates and the
  list of biassing power.
  """

  DEFAULT_ROOTFILE = 'zscan_<BOARDTYPE>_<BOARDID>_<DETID>_<TIMESTAMP>.root'

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
      self.fillroot({"lumival": lumival, "uncval": uncval}, det_id=args.detid)
      self.pbar_data(Lumi=f'{lumival:.2f}+-{uncval:.2f}')


class lowlightcollect(cmdbase.singlexycmd, cmdbase.readoutcmd,
                      cmdbase.rootfilecmd):
  """@brief Collection of low light data at a single gantry position, data will
  be collected without averaging."""
  DEFAULT_ROOTFILE = 'lowlight_<BOARDTYPE>_<BOARDID>_<DETID>_<TIMESTAMP>.root'

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
      readout = readout.tolist()
      self.fillroot({"readout": readout}, {"readout": "var * float64"},
                    det_id=args.detid)
      self.pbar_data(Lumi=f'{readout[-1]:.2}')


class timescan(cmdbase.readoutcmd, cmdbase.rootfilecmd):
  """
  Generate a log of the readout in terms relative to time.
  """
  DEFAULT_ROOTFILE = 'tscan_<TIMESTAMP>.root'

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
      self.fillroot({
          "lumival": lumival,
          "uncval": uncval,
          "S2": s2,
          "S4": s4
      },
                    time=timestamp,
                    det_id=-100)
      self.pbar_data(Lumi=f'{lumival:.2f}+-{uncval:.2f}',
                     Sharp=f'({s2:.1f}, {s4:.1f})')
      time.sleep(args.interval)


class visualmeta(cmdbase.controlcmd):
  """
  @brief Meta class for additional options needed for visual operations
  @ingroup cli_design
  """
  WINDOWS_NAME = 'SIPMCALIB PROCESS'

  def add_args(self):
    self.parser.add_argument('-m',
                             '--monitor',
                             action='store_true',
                             help="""
                             Whether or not to open a window monitoring window
                             (if you are working over SSH, this could be very
                             slow!!)""")
    self.parser.add_argument('--vwait',
                             type=float,
                             default=0.2,
                             help="""
                             Time to wait between motion and image acquisition
                             (seconds)""")

  def show_img(self, args, raw=False):
    if args.monitor:
      cv2.imshow(self.WINDOWS_NAME, np.copy(self.visual.get_image(raw)))
      cv2.waitKey(1)

  def post_run(self):
    cv2.destroyAllWindows()


class visualhscan(cmdbase.hscancmd, visualmeta, cmdbase.rootfilecmd):
  """
  @brief Performing horizontal scan with camera system
  """
  """
  This command assumes that at most a single detector element will be visible to
  the visual system at one time. The command then stores the gantry coordinates
  and the found detector center in pixel cooridnates together, and this is used
  to create the transformation matrix between visual coordinates and gantry
  coordinates for fast visual calibration.
  """

  DEFAULT_ROOTFILE = 'vhscan_<BOARDTYPE>_<BOARDID>_<DETID>_<SCANZ>_<TIMESTAMP>.root'
  HSCAN_ZVALUE = 20
  HSCAN_RANGE = 3
  HSCAN_SEPRATION = 0.5
  VISUAL_OFFSET = True

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--overwrite',
                             action='store_true',
                             help="""
                             Forcing the storage of scan results as 'session
                             information'""")

  def run(self, args):
    """
    As reflection artifacts come and go, we will only use take the gantry
    coordinates where the detector elements has been successfully reconstructed
    in the visual system.
    """
    ## New container to account for det not found in FOV
    gantry_x = []
    gantry_y = []
    reco_x = []
    reco_y = []
    ## Running over mesh.
    for xval, yval in self.start_pbar(zip(args.x, args.y)):
      self.check_handle()
      self.move_gantry(xval, yval, args.scanz)
      time.sleep(args.vwait)

      center = self.visual.get_latest()
      self.show_img(args, False)

      if center.x > 0 and center.y > 0:
        gantry_x.append(xval)
        gantry_y.append(yval)
        reco_x.append(center.x)
        reco_y.append(center.y)

      self.fillroot({
          "center x": center.x,
          "center y": center.y
      },
                    det_id=args.detid)
      self.pbar_data(center=f'({center.x:.0f}, {center.y:.0f})',
                     sharp=f'({center.s2:1f}, {center.s4:.1f})')
    fitx, covar_x = curve_fit(visualhscan.model, np.vstack((gantry_x, gantry_y)),
                              reco_x)
    fity, covar_y = curve_fit(visualhscan.model, np.vstack((gantry_x, gantry_y)),
                              reco_y)

    def meas_str(v, unc):
      return f'{v:.2f}+-{unc:.3f}'

    xx = meas_str(fitx[0], np.sqrt(covar_x[0][0]))
    xy = meas_str(fitx[1], np.sqrt(covar_x[1][1]))
    yx = meas_str(fity[0], np.sqrt(covar_y[0][0]))
    yy = meas_str(fity[1], np.sqrt(covar_y[1][1]))
    self.printmsg(f'Transformation for CamX = ({xx})x + ({xy})y')
    self.printmsg(f'Transformation for CamY = ({yx})x + ({yy})y')

    ## Generating calibration det id if using det coordinates
    detid = int(args.detid)
    # if not detid in self.board.get_all_detectors() and int(args.detid) < 0:
    #   self.board.add_calib_det(args.detid)

    ## Saving rounded coordinates
    if not self.board.visM_hasz(detid, self.gcoder.opz) or args.overwrite:
      self.board.add_visM(detid, self.gcoder.opz,
                          [[fitx[0], fitx[1]], [fity[0], fity[1]]],
                          self.filename)
      self.conditions.update_gantry_and_sipm_conditions('visualhscan', detid,
                                                        args.scanz)

    elif self.board.visM_hasz(detid, self.gcoder.opz):
      if self.prompt_yn(
          f"""
          Transformation equation for z={args.scanz:.1f} already exists,
          overwrite?""", False):
        self.board.add_visM(detid, self.gcoder.opz,
                            [[fitx[0], fitx[1]], [fity[0], fity[1]]],
                            self.filename)
        self.conditions.update_gantry_and_sipm_conditions(
            'visualhscan', detid, args.scanz)

    ## Moving back to center
    self.move_gantry(args.x, args.y, args.scanz)

  @staticmethod
  def model(xydata, a, b, c):
    x, y = xydata
    return a * x + b * y + c


class visualcenterdet(cmdbase.singlexycmd, visualmeta):
  """
  @brief
  Moving the gantry so that the detector element is centered in field of view.
  Before running this function the user must make sure that:

  """
  """

  - That the detector can be found in the camera at the default coordinates.
  - That a working visual-gantry transformation has already been constructed.
  """
  VISUAL_OFFSET = True

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-z',
                             '--scanz',
                             type=float,
                             required=True,
                             help="""
                             Position z to perform centering. User must make sure
                             the visual transformation equation has already been
                             created before.""")
    self.parser.add_argument('--overwrite',
                             action='store_true',
                             help="""
                             Whether to overwrite the existing information or
                             not""")

  def parse(self, args):
    args.calibdet = None
    if self.board.visM_hasz(args.detid, args.scanz):
      args.calibdet = args.detid
    else:
      args.calibdet = next(
          iter([
              x for x in self.board.calib_dets()
              if self.board.visM_hasz(x, args.scanz)
          ]), None)

    if args.calibdet == None:
      self.printerr(f"""
        Motion transformation equation was not found for position
        z={args.scanz:.1f}mm, please run command [visualhscan] first""")
      raise Exception('Transformation equation not found')
    return args

  def run(self, args):
    """
    We will try to get to the final position in 16 motions. As reflection
    artifacts comes and goes, we will try up to 8 times to find the detector
    element in the camera.
    """
    self.move_gantry(args.x, args.y, args.scanz)
    center = None

    for _ in range(16):
      for __ in range(8):
        center = self.visual.get_latest()
        self.show_img(args, False)
        if center.x > 0:
          break
        time.sleep(0.2)

      ## Early exit if det is not found.
      if (center.x < 0 or center.y < 0):
        raise Exception("""
          Detector element in field-of-view lost! Check current camera position
          with command visualdetshow'""")

      deltaxy = np.array([
          self.visual.frame_width() / 2 - center.x,
          self.visual.frame_height() / 2 - center.y
      ])

      motionxy = np.linalg.solve(
          np.array(self.board.get_visM(args.calibdet, self.gcoder.opz)), deltaxy)
      ## Early exit if difference from center is small
      if np.linalg.norm(motionxy) < 0.1: break
      self.move_gantry(self.gcoder.opx + motionxy[0],
                       self.gcoder.opy + motionxy[1], self.gcoder.opz)
      time.sleep(args.vwait)  ## Waiting for the gantry to stop moving

    center = self.visual.get_latest()
    self.printmsg(
      'Gantry position: x={0:.1f} y={1:.1f} | '\
      'Det FOV position: x={2:.1f} y={3:.1f}'.
        format(self.gcoder.opx, self.gcoder.opy, center.x, center.y))
    self.printmsg(
      'Det corner coordinate: '\
      '[{0:d},{1:d}], [{2},{3}], [{4},{5}], [{6},{7}]'.format(
        center.poly_x1, center.poly_y1,
        center.poly_x2, center.poly_y2,
        center.poly_x3, center.poly_y3,
        center.poly_x4, center.poly_y4,
      )
    )

    detid = str(args.detid)

    if not self.board.vis_coord_hasz(detid, self.gcoder.opz) or args.overwrite:
      self.board.add_vis_coord(detid, self.gcoder.opz,
                               [self.gcoder.opx, self.gcoder.opy])
      self.conditions.update_gantry_and_sipm_conditions('visualcenterdet', detid,
                                                        args.scanz)
    elif self.board.vis_coord_hasz(detid, self.gcoder.opz):
      if self.prompt_yn(f"""
                        A visual alignment for z={args.scanz:.1f} already exists
                        for the current session, overwrite?""",
                        default=False):
        self.board.add_vis_coord(detid, self.gcoder.opz,
                                 [self.gcoder.opx, self.gcoder.opy])
        self.conditions.update_gantry_and_sipm_conditions(
            'visualcenterdet', detid, args.scanz)

    # Luminosity calibrated coordinate doesn't exists. displaying the
    # estimated position from calibration det position
    if not self.board.lumi_coord_hasz(detid, self.gcoder.opz):
      deltax = None
      deltay = None
      currentz = self.gcoder.opz
      for calibdet in self.board.calib_dets():
        det = self.board.get_det(calibdet)
        if (self.board.vis_coord_hasz(calibdet, currentz)
            and (self.board.get_latest_entry(args.detid, 'halign') is not None)):
          closestz = self.board.get_closest_calib_z(detid, 'halign', currentz)
          deltax = self.board.get_vis_coord(calibdet, currentz)[0] \
                  - self.board.get_lumi_coord(calibdet, closestz)[0]
          deltay = self.board.get_vis_coord(calibdet, currentz)[1] \
                  - self.board.get_lumi_coord(calibdet, closestz)[2]
        if deltax != None and deltay != None:
          self.printmsg('Estimated Lumi center: x={0} y={1}'.format(
              self.gcoder.opx - deltax, self.gcoder.opy - deltay))


class visualmaxsharp(cmdbase.singlexycmd, cmdbase.zscancmd, visualmeta):
  """
  @brief Moving the gantry to the position such that the image sharpness is
  maximized.
  """
  """
  The user is required to input the z points to scan for maximum sharpness.
  """
  VISUAL_OFFSET = True

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--fitmodel',
                             type=str,
                             default='cubic',
                             choices=['quad', 'cubic', 'gauss'],
                             help='Model to fit the sharpness profile.')

  def run(self, args):
    zval = np.array(args.zlist)
    laplace = []

    for z in args.zlist:
      self.check_handle()
      self.move_gantry(args.x, args.y, z)
      time.sleep(args.vwait)

      center = self.visual.get_latest()
      self.show_img(args, True)
      laplace.append(center.s2)
      # Information
      self.update(f"z position: {z:.1f} | sharpness: {laplace[-1]:6.2f}")

    # Truncating data set to only valid values
    laplace = np.array(laplace)
    mask = laplace > 0
    laplace = laplace[mask]
    zval = zval[mask]

    model = visualmaxsharp.quad_model() if args.fitmodel == 'quad' else \
            visualmaxsharp.gauss_model() if args.fitmodel == 'gauss' else \
            visualmaxsharp.cubic_model()

    # First fit over full scan range
    fit, cov = curve_fit(
        model,
        zval,
        laplace,
        p0=[zval[np.argmax(laplace)], *model.init_guess],
        # Initial guess
        bounds=([np.min(args.zlist),
                 *model.bounds[0]], [np.max(args.zlist), *model.bounds[1]]),
        maxfev=int(1e4))
    self.printmsg(f"Target z position: {fit[0]:.2f}mm (actual: {fit[0]:.1f}mm)")
    self.move_gantry(args.x, args.y, fit[0])

  """
  Models for running the sharpness fit profile, defined as static methods. Notice
  the various models be defined such that:

  - In the implementation of the __call__ method
    - `z` is the first argument
    - `z_0` indicating the maximum sharpness point must be the second argument
  - provide the following variables:
    - `init_guess` indicating the estimated stating point of the parameters other
      than z_0
    - `bounds` indicating the boundaries of the parameters other than z_0 The
      initial value and boundaries of z0 will be determined from the data.
  """

  class cubic_model(object):
    def __init__(self):
      self.init_guess = [0, -1000, 0]
      self.bounds = ([-np.inf, -np.inf, -np.inf], [np.inf, 0, np.inf])

    def __call__(self, z, z0, a, b, c):
      return a * (z - z0)**3 + b * (z - z0)**2 + c

  class quad_model(object):
    def __init__(self):
      self.init_guess = [-1000, 0]
      self.bounds = ([-np.inf, -np.inf], [0, np.inf])

    def __call__(self, z, z0, a, c):
      return a * (z - z0)**2 + c

  class gauss_model(object):
    def __init__(self):
      self.init_guess = [1000, 10, 0]
      self.bounds = ([0, 0, -np.inf], [np.inf, np.inf, np.inf])

    def __call__(self, z, z0, a, b, c):
      return a * exp(-(z - z0)**2 / (2 * b**2)) + c


class visualzscan(cmdbase.singlexycmd, cmdbase.zscancmd, visualmeta,
                  cmdbase.rootfilecmd):
  """
  @brief Scanning focus to calibrate z distance
  """
  VISUAL_OFFSET = True
  DEFAULT_ROOTFILE = 'vscan_<DETID>_<TIMESTAMP>.root'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    pass

  def run(self, args):
    for z in self.start_pbar(args.zlist):
      # Checking termination signal
      self.check_handle()
      self.move_gantry(args.x, args.y, z)
      time.sleep(args.wait)

      center = self.visual.get_latest()
      self.show_img(args, True)
      laplace.append(center.sharpness)
      reco_x.append(center.x)
      reco_y.append(center.y)
      reco_a.append(center.area)
      reco_d.append(center.maxmeas)
      self.fillroot(
          {
              "laplace": laplace[-1],
              "center x": center.x,
              "center y": center.y,
              "center area": center.area,
              "center maxmeas": center.maxmeas
          },
          det_id=args.detid)
      self.pbar_data(sharpness=f'({center.s2:.1f}, {center.s4:.1f})',
                     reco=f'({center.x:.0f}, {center.y:.0f})',
                     measure=f'({center.area:.0f}, {center.maxmeas:.0f})')
