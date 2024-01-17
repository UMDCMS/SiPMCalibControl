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


class set_visual(cmdbase.controlcmd):
  """@brief Defining the parameters used for finding the detector in the field
  of view."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--devpath',
                             type=str,
                             help="""
                             Device path for the primary camera, should be
                             something like `/dev/video<index>`.""")

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
    self.init_device(args)

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

  def init_device(args):
    # Early exit if the dev path is not specified by the user
    if not args.devpath:
      return

    if 'dummy' in args.camdev:
      self.printwarn('Initializing dummy camera device')
      # TODO: Properly setting up the dummy visual system
    else:
      self.visual.init_dev(args.camdev)


class get_visual(cmdbase.controlcmd):
  """@brief Getting the visual settings"""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, args):
    table = [('Device', str(self.visual.dev_path)),  #
             (f'Threshold', f'{self.visual.threshold:.0f}'),
             (f'Blur', f'{self.visual.blur_range:d}', '[pix]'),
             (f'Max Lumi', f'{self.visual.lumi_cutoff:.0f}'),
             (f'Min Size', f'{self.visual.size_cutoff:d}', '[pix]'),
             (f'Ratio', f'{self.visual.ratio_cutoff:.3f}'),
             (f'Poly', f'{self.visual.poly_range:.3f}'), ]
    self.devlog("Visual").log(fmt.logging.INT_INFO, '', extra={'table': table})


class visualshowdet(cmdbase.controlcmd):
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
    self.parser.add_argument('--vwait',
                             type=float,
                             default=0.2,
                             help="""
                             Time to wait between motion and image acquisition
                             (seconds)""")

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
        cv2.imshow(self.WINDOWS_NAME, np.copy(self.visual.get_image(raw)))
        cv2.waitKey(1)
        time.sleep(args.vwait)
      except:
        break

  def post_run(self):
    cv2.destroyAllWindows()


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
