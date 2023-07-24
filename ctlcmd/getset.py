"""
  getset.py

  Commands that are used for looking up, displaying and modifying session
  parameters. This includes loading and saving the master coordinate calibration
  results, setting the readout devices, and commands used to stall the program.
  Notice that "setting the readout devices" will only handle the opening and
  closing of device interfaces, not the actual readout device internal settings.
  That should be handled in their designate command files.
"""

import ctlcmd.cmdbase as cmdbase
import cmod.fmt as fmt
import argparse
import re
import os
import sys
import time


class exit(cmdbase.controlcmd):
  """@brief Command for exiting the main session"""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, args):
    if self.prompt_yn("""Exiting this will terminate the session and all
                      calibration variables (results are still on disk). Are you
                      sure you want to exit?""",
                      default=False):
      self.printmsg("Sending gantry home...")
      # Fast motion to somewhere close to home
      self.move_gantry(1, 1, 1)
      # Activate send home
      try:
        self.gcoder.sendhome(True, True, True)
      except Exception as err:
        pass
      return cmdbase.controlcmd.TERMINATE_SESSION


class set(cmdbase.controlcmd):
  """
  @brief Setting calibration system devices. This will only modify opening and
  closing the interface, not the actual operation of the various interfaces. See
  visualset, picoset, and drsset for more information.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--printerdev',
                             type=str,
                             help="""
                             Device path for the 3d printer. Should be something
                             like `/dev/tty<SOMETHING>`.""")
    self.parser.add_argument('--camdev',
                             type=str,
                             help="""
                             Device path for the primary camera, should be
                             something like `/dev/video<index>`.""")
    self.parser.add_argument('--picodevice',
                             type=str,
                             help="""
                             The serial number of the pico-tech device for
                             dynamic light readout""")
    self.parser.add_argument('--drsdevice',
                             type=str,
                             help='Code flag to refresh DRS device')

  def run(self, args):
    """
    For the sake of clarity, device settings is split into each of their
    functions. Notice that all function should have exception guards so the
    subsequent settings can still be set if settings for one particular device
    is bad or not available.
    """
    if args.camdev:
      self.set_camera(args)
    if args.printerdev:
      self.set_printer(args)
    if args.picodevice:
      self.set_picodevice(args)
    if args.drsdevice:
      self.set_drs(args)

  def set_camera(self, args):
    """Setting up the camera system, given /dev/video path"""
    if (not self.is_dummy_dev(args.camdev, 'Visual System')
        and args.camdev != self.visual.dev_path):
      try:
        self.visual.init_dev(args.camdev)
      except RuntimeError as err:
        self.devlog('Visual').error(str(err))
        self.printwarn('Initializing webcam has failed, skipping over setting')

  def set_printer(self, args):
    """Setting up the gantry system, given the /dev/USB path"""
    if (not self.is_dummy_dev(args.printerdev, 'Printer')
        and args.printerdev != self.gcoder.dev_path):
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
        self.move_gantry(0.1, 0.1, 0.1)

  def set_picodevice(self, args):
    """Setting up the pico device, Skipping if dummy path detected """
    if not self.is_dummy_dev(args.picodevice, 'PicoScope'):
      if self.pico is None:
        self.printwarn("Picoscope device is not available, ignoring...")
      else:
        try:
          self.pico.init()
        except RuntimeError as err:
          self.devlog('PicoUnit').error(str(err))
          self.printwarn('Picoscope device is not properly set!')

  def set_drs(self, args):
    """Setting up the DRS4. Skipping if dummy path is detected"""
    if not self.is_dummy_dev(args.drsdevice, 'DRS4'):
      if self.drs is None:
        self.printwarn("DRS device is not available, ignoring...")
      else:
        try:
          self.drs.init()
        except RuntimeError as err:
          self.devlog('DRSContainer').error(str(err))
          self.printwarn('DRS device is not properly set!')

  def is_dummy_dev(self, dev, device_name):
    """
    Simple check for illegal device string, so that certain hardware interfaces
    can be disabled. A legal device string must start with the '/dev' prefix and
    must not contain the "dummy" string.
    """
    is_dummy = not dev.startswith('/dev') or 'dummy' in dev
    if is_dummy:
      self.printwarn(f"""
        Path [{dev}] for device [{device_name}] is as dummy path, skipping setup
        of device. If not already setup, then future commands using
        [{device_name}] may misbehave.""")
    return is_dummy


class get(cmdbase.controlcmd):
  """@brief Printing out the session parameters, and equipment settings."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--printerdev', action='store_true')
    self.parser.add_argument('--camdev', action='store_true')
    self.parser.add_argument('--align', action='store_true')
    self.parser.add_argument('--pico', action='store_true')
    self.parser.add_argument('--drs', action='store_true')
    self.parser.add_argument('-a', '--all', action='store_true')

  def run(self, args):
    if args.printerdev or args.all:
      self.print_printer()
    if args.camdev or args.all:
      self.print_camera()
    if args.align or args.all:
      self.print_alignment()
    if args.pico or args.all:
      self.print_pico()
    if args.drs or args.all:
      self.print_drs()

  def print_pico(self):
    logger = self.devlog('PicoUnit')
    info = self.pico.dumpinfo()
    info_table = [[x.strip()
                   for x in line.split('|')]
                  for line in info.split('\n')]
    logger.log(fmt.logging.INT_INFO, '', extra={'table': info_table})

  def print_printer(self):
    logger = self.devlog("GCoder")
    level = fmt.logging.INT_INFO
    logger.log(level, 'device: ' + str(self.gcoder.dev_path))
    logger.log(
        level, f'current coordinates:' + f' x{self.gcoder.opx:.1f}' +
        f' y{self.gcoder.opy:.1f}' + f' z{self.gcoder.opz:.1f}')
    settings = self.gcoder.getsettings().split('\necho:')
    logging.log(level, '\n'.join(line))

  def print_camera(self):
    table = [('Device', str(self.visual.dev_path)),  #
             (f'Threshold', f'{self.visual.threshold:.0f}'),
             (f'Blur', f'{self.visual.blur_range:d}', '[pix]'),
             (f'Max Lumi', f'{self.visual.lumi_cutoff:.0f}'),
             (f'Min Size', f'{self.visual.size_cutoff:d}', '[pix]'),
             (f'Ratio', f'{self.visual.ratio_cutoff:.3f}'),
             (f'Poly', f'{self.visual.poly_range:.3f}'), ]
    self.devlog("Visual").log(fmt.logging.INT_INFO, '', extra={'table': table})

  def print_alignment(self):
    lumi_header = fmt.GREEN('[LUMI_ALIGN]')
    matrix_header = fmt.GREEN('[VIS_MATRIX]')
    vis_header = fmt.GREEN('[VIS__ALIGN]')
    det_format = fmt.YELLOW(' DET{0:3d}')

    for detid in self.board.dets():
      det_str = det_format.format(int(detid))
      det = self.board.get_det(detid)
      for z in det.lumi_coord:
        self.printmsg(
            lumi_header + det_str,
            'x:{0:.2f}+-{1:.2f} y:{2:.2f}+-{3:.2f} | at z={4:.1f}'.format(
                det.lumi_coord[z][0], det.lumi_coord[z][2], det.lumi_coord[z][1],
                det.lumi_coord[z][3], z))
      for z in det.vis_M:
        self.printmsg(matrix_header + det_str, '{0} | at z={1:.1f}'.format(
            det.vis_M[z], z))
      for z in det.vis_coord:
        self.printmsg(
            vis_header + det_str, 'x:{0:.2f} y:{1:.2f} | at z={2:.1f}'.format(
                det.vis_coord[z][0], det.vis_coord[z][1], z))

  def print_drs(self):
    self.printmsg(str(self.drs.is_available()))

class history(cmdbase.savefilecmd):
  """
  Getting the input history. Notice that this will only include the user input
  history. Commands in the runfile will note be expanded.
  """
  DEFAULT_SAVEFILE = None  # Do not attempt to save the command history on call.

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--successful',
                             '-s',
                             action='store_true',
                             help="""
                             Keep only the commands the successfully executed
                             without error (user interuptions would be treated
                             as errors!)""")

  def run(self, args):
    """
    Getting the command execution record based on the the logging entries.
    """
    cmd_record = [
        x for x in self.cmd.mem_handle.record_list
        if x.levelno == fmt.logging.CMD_HIST and 'stop' in x.args
    ]
    if args.successful:  # Additional filtering for successfully executed commands
      cmd_record = [x for x in cmd_record if x.args[1] == self.EXIT_SUCCESS]

    self.screen_history(cmd_record)
    if self.savefile:
      self.file_history(cmd_record)

  def screen_history(self, cmd_record):
    """
    @brief Printing the cmd history dump to screen

    @details We will only include the exceution status and the command itself
    (no time stamps!) for a brevity.
    """
    def stat_str(stat_no):
      return fmt.RED(   "[PARSE ERROR ]") if stat_no == self.PARSE_ERROR else \
             fmt.RED(   "[EXEC ERROR  ]") if stat_no == self.EXECUTE_ERROR else \
             fmt.YELLOW("[INTERRUPTED ]") if stat_no == self.TERMINATE_CMD else \
             fmt.GREEN( "[EXEC SUCCESS]")

    cmd_lines = [stat_str(x.args[1]) + ' ' + x.msg for x in cmd_record]
    if len(cmd_lines):
      self.logger.log(fmt.logging.INT_INFO, '\n'.join(cmd_lines))

  def file_history(self, cmd_record):
    """
    @brief Saving the cmd history dump to the savefile

    @details The first 2 columns would be the time stamp (for potentially
    debugging), and the exit status string. The latter entires would be the
    command executed.
    """
    def stat_str(record):
      """Converting execute status code to human readable string"""
      stat_no = record.args[1]
      return "PARSE_ERROR"   if stat_no == self.PARSE_ERROR else   \
             "EXECUTE_ERROR" if stat_no == self.EXECUTE_ERROR else \
             "INTERRUPTED"   if stat_no == self.TERMINATE_CMD else \
             "EXIT_SUCCESS"

    for rec in cmd_record:
      self.savefile.write(
          f'{fmt.record_timestamp(rec):s} {stat_str(rec):15s} {rec.msg:s}\n')


class logdump(cmdbase.savefilecmd):
  """
  @brief Dumping log entries into to a file.
  """
  DEFAULT_SAVEFILE = 'logdump_<TIMESTAMP>.log'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--exclude',
                             '-x',
                             type=str,
                             nargs='*',
                             choices=list(fmt.__all_logging_levels__.values()),
                             default=['TRACEBACK', 'HW_DEBUG', 'INT_INFO'],
                             help="""Removing log-levels to avoid being too
                                  verbose in output file. Default =
                                  %(default)s""")
    self.parser.add_argument('--format',
                             type=str,
                             choices=['line', 'json'],
                             default='line',
                             help="""Format to dump the file into (json is
                                  eaiser to reconstruct for advanced processing,
                                  but difficult for command-line based
                                  piping operations (Default=%(default)s)""")

  def run(self, args):
    """
    As log parsing is more verbose, here will call the in-built method in the
    fmt file for processing the file.
    """
    if args.format == 'line':
      self.cmd.mem_handle.dump_lines(self.savefile, exclude=args.exclude)
    else:
      self.cmd.mem_handle.dump_json(self.savefile, exclude=args.exclude)


class wait(cmdbase.controlcmd):
  """
  @brief Suspending the interactive session for N seconds, or until a
  confirmation string is entered by user. Wait can be terminated early using
  Ctl+C.

  <help link>
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    group = self.parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--time',
                       '-t',
                       type=float,
                       help='Time to suspend session (seconds)')
    group.add_argument('--message',
                       type=str,
                       nargs='+',
                       help="""The first string would be the key that that user
                            inputs to release the wait, the trailing string
                            would be a message to display during wait time""")

  def parse(self, args):
    if args.time:  # Pausing by time
      if args.time < 0:
        raise ValueError('Pause time must be positive!')
    else:  # Pausing by message:
      args.userkey = args.message[0]
      args.message = ' '.join(
          args.message[1:]) + f'<br>Enter [{args.userkey}] to continue: '
    return args

  def run(self, args):
    if args.time:
      self.wait_fixed_time(args)
    else:
      self.wait_user_input(args)

  def wait_fixed_time(self, args):
    """Waiting for a fixed time. Here we also include a progress bar for easier
    checking of progress (We are expecting wait times on the order of seconds"""
    start_time = time.time()
    prev_time = start_time
    curr_time = start_time
    self.start_pbar(total=int(args.time))
    while (curr_time - start_time) < args.time:
      self.check_handle()
      time.sleep(0.01)
      curr_time = time.time()
      if curr_time - prev_time > 1.0:
        self.pbar.update()
        self.pbar_data(Total=args.time)
        prev_time = curr_time
    if self.pbar.n != self.pbar.total:  # Forcing complete progress bard to appear.
      self.pbar.update(self.pbar.total - self.pbar.n)

  def wait_user_input(self, args):
    self.prompt_input(args.message, allowed=[args.userkey])


class runfile(cmdbase.controlcmd):
  """
  @brief Running a file with a list of commands.
  """
  """
  Notice that while runfiles can be called recursively, you cannot call runfiles
  that have already been called, as this will cause infinite recursion. If any
  command in the command file fails, the whole runfile call will be terminated to
  prevent user error from damaging the gantry.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('file',
                             nargs=1,
                             type=str,
                             help="""
                             Runfile to use. Relative paths will be evaluated
                             from the current working directory.""")

  def parse(self, args):
    """Making sure the target is a readable file."""
    args.file = args.file[0]
    if not os.path.isfile(args.file):
      raise ValueError('Specified path is not a file!')
    return args

  def run(self, args):
    """
    The command will infer a runfile stack in the controlterm instance to keep
    track of which files has already been invoked by the runfile command. The
    last file in the stack will be opened and executed per-line.
    """
    if not hasattr(self.cmd, 'runfile_stack'):
      self.cmd.runfile_stack = []

    if args.file in self.cmd.runfile_stack:
      self.error_exit_run(f"""
        File [{args.file}] has already been called! This indicates there is some
        error in user logic. Exiting the top level runfile command.""")
    else:
      self.cmd.runfile_stack.append(args.file)

    with open(args.file) as f:
      for line in f.readlines():
        line = line.strip()
        self.check_handle()
        self.printmsg(line)
        status = self.cmd.onecmd(line)
        if status != cmdbase.controlcmd.EXIT_SUCCESS:
          self.error_exit_run(f"""
            Command [{line}] in file [{args.file}] has failed. Exiting top level
            runfile command.""")
    self.cmd.runfile_stack.pop(-1)

  def error_exit_run(self, msg):
    """
    Save exit on error to ensure that the runfile stack is properly cleared out.
    """
    self.cmd.runfile_stack = []
    raise ValueError(msg)

  def complete(self, text, line, start_index, end_index):
    return cmdbase.controlcmd.globcomp(text)
