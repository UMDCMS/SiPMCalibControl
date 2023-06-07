"""

tbcmd.py

Commands specific to the control of the tileboard testers. To help distinguish
the these command, all commands defined in this file should have the "tb"
prefix into the command name.

"""

import ctlcmd.cmdbase as cmdbase
import time, yaml
import numpy as np

from scipy.optimize import curve_fit
from cmod.TBController import TBController


class tbset(cmdbase.controlcmd):
  """
  @brief Setting up connections to the tileboard tester
  """
  def __init__(self, cmd):
    super().__init__(cmd)

  def add_args(self):
    self.parser.add_argument('--ip',
                             type=str,
                             required=True,
                             help='IP address of the tileboard tester')
    self.parser.add_argument('--ports',
                             type=int,
                             nargs=3,
                             required=True,
                             help="""Ports to the daq/fast control and slow
                                  control servers on the tileboard tester""")
    self.parser.add_argument('--keyfile',
                             type=str,
                             required=True,
                             help="""Path to SSH key for tileboard tester""")
    self.parser.add_argument('--configfile',
                             type=str,
                             default='cfg/tbc_yaml/roc_config_ConvGain4.yaml',
                             help="""Default configuration for load to the
                                  servers instances on connection
                                  establishment""")

  def parse(self, args):
    args.daq_port = args.ports[0]
    args.cli_port = args.ports[1]
    args.i2c_port = args.ports[2]
    return args

  def run(self, args):
    self.tbc.init(ip=args.ip,
                  daq_port=args.daq_port,
                  cli_port=args.cli_port,
                  i2c_port=args.i2c_port,
                  ssh_key=args.keyfile,
                  config_file=args.configfile)


class tb_saveconfig(cmdbase.savefilecmd):
  """
  @brief Saving the current configuration to a file
  """
  def __init__(self, cmd):
    super().__init__(cmd)

  def parse(self, args):
    if args.wipefile:
      self.printwarn("""For this operation, the "wipefile" options will be
                     ignored, as you should not be concatenating
                     configuration files""")
    return args

  def run(self, args):
    """
    This method is based on the saveFullConfig method defined in the
    hexactrl-scripts.utils [file][repo].

    [repo]: https://gitlab.cern.ch/hgcal-daq-sw/hexactrl-script/-/blob/master/util.py
    """

    full_config = {
        k: v
        for k, v in self.tbc.i2c_socket.yaml_config.items()
        if 'roc_s' in k  # I2C settings will always have a prefix
    }
    full_config['daq'] = self.tbc.daq_socket.yaml_config['daq']
    full_config['global'] = self.tbc.cli_socket.yaml_config['global']

    yaml.dump(full_config, self.savefile)


class tb_levelped(cmdbase.savefilecmd):
  """
  @brief Running the routine to auto-level the pedestal to some target value.
  """
  DEFAULT_SAVEFILE = 'TB_levelped_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    super().__init__(cmd)

  def add_args(self):
    self.parser.add_argument('--target',
                             type=int,
                             default=70,
                             help='Target final pedestal value')
    self.parser.add_argument('--samples',
                             type=int,
                             default=2000,
                             help='Number of events used to extract pedestal')

  def run(self, args):
    self.tbc.daq_socket.enable_fast_commands(random=1)
    self.tbc.daq_socket.l1a_settings(bx_spacing=45)
    default_dacb = self.get_current_dacb()

    main_data = {}

    for shift in self.start_pbar(range(-5, 5)):
      self.check_handle()
      updated_dacb = {c: v + shift for c, v in default_dacb.items()}
      main_data.update(self.acquire_single(updated_dacb, args.samples))

    corrected_dacb = self.calc_corrected_dacb(main_data, args.target)
    main_data.update(self.acquire_single(corrected_dacb, args.samples))

    for (ch, dacb), (ped, noise) in main_data.items():
      check_val = 1 if corrected_dacb[ch] == dacb else \
                  -1 if default_dacb[ch] == dacb else \
                  0
      self.write_standard_line((dacb, ped, noise, check_val), ch)
      print("dacb "+dacb+" ped "+ped+" noise "+noise+ " check_val "+check_val+" ch "+ch)

    print(corrected_dacb)

  def acquire_single(self, dacb_map: dict[int, int], nevents: int) -> dict:
    """
    Given a single channel-DACb setting map, run the data acquisition routine to
    get a pedestal/noise estimate.
    """
    for channel in dacb_map.keys():
      self.tbc.i2c_socket.configure(yaml_config=TBController.make_deep(
          'roc_s0', 'sc', 'ch', channel, 'Dacb', dacb_map[channel]))
    arr = self.tbc.acquire(nevents)
    return {(ch, dacb_map[ch]): (np.mean(arr.adc[arr.channel == channel]),
                                 np.std(arr.adc[arr.channel == channel]))
            for ch in dacb_map.keys()}

  def get_current_dacb(self) -> dict:
    """
    Getting the DACb setting stored in the i2c_socket instance right now.
    """
    return {
        ch: self.tbc.i2c_socket.yaml_config['roc_s0']['sc']['ch'][ch]['Dacb']
        for ch in self.tbc.i2c_socket.yaml_config['roc_s0']['sc']['ch'].keys()
    }

  def calc_corrected_dacb(self, data, target) -> dict:
    """
    Given data in the format of {(channel, dacb): (pedestal, noise)} return a
    {channel:dacb} dictionary, which attempt to correct the DAC bit value to be
    as close to the target value as possible
    """
    def lin_f(x, a, b):
      """Pedestal value as a function of DACb is very linear"""
      return a * x + b

    ret = {}

    for ch in sorted(set([p[0] for p in data.keys()])):
      x = [p[1] for p in data.keys() if p[0] == ch]
      y = [v[0] for p, v in data.items() if p[0] == ch]
      ye = [v[1] for p, v in data.items() if p[0] == ch]
      p, c = curve_fit(lin_f, x, y, sigma=ye)
      ret[ch] = round((target - p[1]) / p[0])  # Rounding to closest integer

    return ret


class tb_test(cmdbase.controlcmd):
  """
  @brief my test
  """
  def __init__(self, cmd):
    super().__init__(cmd)

  def run(self, args):
    self.tbc.daq_socket.enable_fast_commands(random=1)
    self.tbc.daq_socket.l1a_settings(bx_spacing=45)
    print(self.tbc.acquire(100)[20:30])
