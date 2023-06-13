"""
viscmd.py

Commands for interacting and using the visual system for positional calibration.

"""
import ctlcmd.cmdbase as cmdbase
import cmod.visual as vis
import cmod.fmt as fmt
import numpy as np
from scipy.optimize import curve_fit
import time
import cv2
import copy


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


class visualset(cmdbase.controlcmd):
  """@brief Defining the parameters used for finding the detector in the field of view."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--threshold',
                             '-t',
                             type=float,
                             help="""
                             Grayscale threshold to perform contouring algorithm
                             [0-255]""")
    self.parser.add_argument('--blur',
                             '-b',
                             type=int,
                             help="""
                             Blur size to perform to the image before contouring
                             to avoid picking up noise [pixels]""")
    self.parser.add_argument('--lumi',
                             '-l',
                             type=int,
                             help="""
                             Maximum luminosity threshold of the interior of a
                             contour to be selected as a det candidate (typically
                             0-255)""")
    self.parser.add_argument('--size',
                             '-s',
                             type=int,
                             help="""
                             Minimum size of a contour to be selected as a det
                             candidate [pixels]""")
    self.parser.add_argument('--ratio',
                             '-r',
                             type=float,
                             help="""
                             Maximum Ratio of the two dimension of a contour to
                             be selected as a det candidate (>1)""")
    self.parser.add_argument('--poly',
                             '-p',
                             type=float,
                             help="""
                             Relative tolerance for performing polygon
                             approximation algorithm (0, 1)""")

  def run(self, args):
    if args.threshold:
      self.visual.threshold = args.threshold
    if args.blur:
      self.visual.blur_range = args.blur
    if args.lumi:
      self.visual.lumi_cutoff = args.lumi
    if args.size:
      self.visual.size_cutoff = args.size
    if args.ratio:
      self.visual.ratio_cutoff = args.ratio
    if args.poly:
      self.visual.poly_range = args.poly


class visualhscan(cmdbase.hscancmd, visualmeta,cmdbase.rootfilecmd):
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

      self.fillroot({"center x":center.x,"center y":center.y},det_id=args.detid) 
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
    detid = str(args.detid)
    if not detid in self.board.dets() and int(args.detid) < 0:
      self.board.add_calib_det(args.detid)

    ## Saving rounded coordinates
    if not self.board.visM_hasz(detid, self.gcoder.opz) or args.overwrite:
      self.board.add_visM(detid, self.gcoder.opz,
                          [[fitx[0], fitx[1]], [fity[0], fity[1]]])
    elif self.board.visM_hasz(detid, self.gcoder.opz):
      if self.prompt_yn(
          f"""
          Transformation equation for z={args.scanz:.1f} already exists,
          overwrite?""", False):
        self.board.add_visM(detid, self.gcoder.opz,
                            [[fitx[0], fitx[1]], [fity[0], fity[1]]])

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
      args.calibdet = args.detit
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
    elif self.board.vis_coord_hasz(detid, self.gcoder.opz):
      if self.prompt_yn(f"""
                        A visual alignment for z={args.scanz:.1f} already exists
                        for the current session, overwrite?""",
                        default=False):
        self.board.add_vis_coord(detid, self.gcoder.opz,
                                 [self.gcoder.opx, self.gcoder.opy])

    # Luminosity calibrated coordinate doesn't exists. displaying the
    # estimated position from calibration det position
    if not self.board.lumi_coord_hasz(detid, self.gcoder.opz):
      deltax = None
      deltay = None
      currentz = self.gcoder.opz
      for calibdet in self.board.calib_dets():
        det = self.board.get_det(calibdet)
        if (self.board.vis_coord_hasz(calibdet, currentz)
            and any(det.lumi_coord)):
          closestz = min(det.lumi_coord.keys(), key=lambda x: abs(x - currentz))
          deltax = self.board.get_vis_coord(calibdet, currentz)[0] \
                  - self.board.get_lumi_coord(calibdet, closestz)[0]
          deltay = self.board.get_vis_coord(calibdet, currentz)[1] \
                  - self.board.get_lumi_coord(calibdet, closestz)[2]
        if deltax != None and deltay != None:
          self.printmsg('Estimated Lumi center: x={0} y={1}'.format(
              self.gcoder.opx - deltax, self.gcoder.opy - deltay))


class visualmaxsharp(cmdbase.singlexycmd, cmdbase.zscancmd, visualmeta):
  """
  @brief Moving the gantry to the position such that the image sharpness is maximized.
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


class visualsaveframe(cmdbase.controlcmd):
  """
  @brief Saving the current image to some path
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--saveimg',
                             type=str,
                             required=True,
                             help='Local path to store image file')
    self.parser.add_argument('--raw',
                             action='store_true',
                             help='Store raw image or processes image')

  def run(self, args):
    self.visual.save_image(args.saveimg, args.raw)


class visualzscan(cmdbase.singlexycmd, cmdbase.zscancmd,
                  visualmeta,cmdbase.rootfilecmd):
  """
  @brief Scanning focus to calibrate z distance
  """
  VISUAL_OFFSET = True
  DEFAULT_ROOTFILE= 'vscan_<DETID>_<TIMESTAMP>.root'

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
      self.fillroot({"laplace":laplace[-1],"center x":center.x,"center y":center.y,"center area":center.area,"center maxmeas":center.maxmeas},det_id=args.detid)
      self.pbar_data(sharpness=f'({center.s2:.1f}, {center.s4:.1f})',
                     reco=f'({center.x:.0f}, {center.y:.0f})',
                     measure=f'({center.area:.0f}, {center.maxmeas:.0f})')
class visualshowdet(visualmeta):
  """@brief Display of detector position, until termination signal is obtained."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--raw',
                             '-r',
                             action='store_true',
                             help="""
                             Show the raw image without image processing
                             lines""")

  def parse(self, args):
    args.monitor = True  # Forcing to be true.
    return args

  def run(self, args):
    self.printmsg("PRESS CTL+C to stop the command")
    self.printmsg("Legend")
    self.printmsg("Failed contor ratio requirement")
    self.printmsg(fmt.GREEN("Failed area luminosity requirement"))
    self.printmsg(fmt.YELLOW("Failed rectangular approximation"))
    self.printmsg(fmt.CYAN("Candidate contour (not largest)"))
    while True:
      try:
        self.check_handle()
      except:
        break

      self.show_img(args, args.raw)
      time.sleep(args.vwait)
