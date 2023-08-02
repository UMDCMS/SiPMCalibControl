"""
@file TBController.py
"""
import zmq, yaml, time, paramiko, copy, uproot, os
import awkward as ak
import cmod.fmt as fmt
import cmod.rocv2 as rocv2


class TBController(object):
  """
  @ingroup hardware

  @brief Object for interacting with the Tileboard controller

  @details The object defined in this module sets up the connections to the
  tileboard tester over an network connection to allow for fast/slow control and
  data pulling. The client objects defined in this object is based on the
  objects found in the official [hexaboard control software][zmq_controller],
  with additional specialization and process reduction to make the easier to
  interface with the framework used for controlling other subsystems. We also
  assume that the appropriate firmware, software and utility scripts have
  already been setup on the tileboard tester unit.

  To avoid clutter, the detailed implementation of the various socket classes
  will not completely listed in the hardware group, and this main container
  class will only contain the high-level functions. You can still find out how
  the various sockets are implemented in the following links

  - For a generic overview of how a ZMQ socket is defined and used in the
    context of the hexaboard control software, see the
    cmod.TBController.ZMQController class.
  - For the ZMQ socket that is specialized for the slow (I2C) controls, see the
    cmod.TBController.I2CController class.
  - For the ZQM sockets that are specialized for fast control and data
    extraction from the tileboard, see the cmod.TBController.DAQController
    class.

  This main container class includes the actual instances for a slow (i2c)
  control, fast control, fast readout socket connection triplet, as well as a
  paramiko ssh connection to the tileboard tester to allow for additional
  control over the system (tileboard server startup and data format conversion).
  This class expects the slow/fast control servers to be running on the
  tileboard tester, and the readout server to be running on same machine the
  control instance in on but outside the main docker container instance
  (localhost will still work for connecting with the data puller server). For
  the implementation of the various classes, we stick with the paradigm of
  having the the constructor do nothing, and have the instance be properly
  initialized on some `init` call.

  One pattern that we will not attempt to abstract further the data acquisition
  routine:

  - We first push the data pulling configurations the server
  - Then we call the data acquisition
  - Finally we clear the various ob


  [zmq_controller]:
  https://gitlab.cern.ch/hgcal-daq-sw/hexactrl-script/-/blob/master/zmq_controler.py
  """
  def __init__(self):
    """
    @brief Creating the instances of the controller sockets.

    @No actions should be performed here to actually connect to the server
    instances, as that should be handled by the `init` method.
    """
    self.daq_socket = DAQController()
    self.pull_socket = DAQController()
    self.i2c_socket = I2CController()
    self.ssh_control = paramiko.SSHClient()
    self.ssh_control.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  def init(self,
           ip,
           daq_port,
           pull_port,
           i2c_port,
           config_file,
           ssh_key,
           pull_ip='localhost',
           restart_server=False):
    """
    @brief Setting up the various socket connections.

    @details The user should include the network settings required for the
    various sockets, as well as the "default" configuration file we should flush
    to the server sessions. One setting that we overwrite is have the data
    pulling socket have a to matching the IP address to the tileboard connect
    (as the original expected the data pulling client to run on the same machine
    that is hosting the data pulling server).
    """
    # Setting up the ssh connection to handle data file manipulation
    self.ssh_control.connect(hostname=ip,
                             username='HGCAL_dev',
                             key_filename=ssh_key)

    if restart_server:
      self.tb_serverdown()
      self.tb_serverup()

    # Connecting the sockets
    self.daq_socket.init(ip=ip, port=daq_port, config_file=config_file)
    self.i2c_socket.init(ip=ip, port=i2c_port, config_file=config_file)
    self.pull_socket.init(ip=pull_ip, port=cli_port, config_file=config_file)

    # Letting the data puller understand where to pull the data from.
    self.pull_socket.yaml_config['global']['serverIP'] = self.daq_socket.ip

  def tb_serverup(self):
    """Starting the server instances via an ssh command."""
    # Here we assume that the server startup script is available on the
    # tileboard tester.
    self.tbssh_command('/home/HGCAL_dev/scripts/serverup.sh')
    # Waiting 10 seconds for everything to settle (the I2C server performs a
    # slow scan on start up)
    time.wait(10)

  def tb_serverdown(self):
    """Closing the server instances"""
    # Here we assume that the server startup script is available on the
    # tileboard tester.
    self.tbssh_command('/home/HGCAL_dev/scripts/serverdown.sh')
    # Waiting 10 seconds for everything to settle (the I2C server performs a
    # slow scan on start up)
    time.wait(10)

  def acquire(self, n_events):
    """
    @brief Acquiring n_events worth of data.

    @details Flushing the data puller configurations to the zmq-client instance.
    We split this into a separate function in case we need to run multiple data
    acquisition routines with different slow settings (frequently used for
    configuration scanning routines.)
    """
    # Number of events is set by the the daq_socket yaml configuration
    self.daq_socket.yaml_config['daq']['NEvents'] = str(n_events)
    # Additional settings for the client
    remote_dir = '/tmp/'
    remote_name = 'data_acquire'

    self.pull_socket.yaml_config['global']['outputDirectory'] = remote_dir
    self.pull_socket.yaml_config['global']['run_type'] = remote_name

    self.pull_socket.configure()
    self.daq_socket.configure()

    self.pull_socket.start()
    self.daq_socket.start()
    while not self.daq_socket.is_complete():
      time.sleep(0.01)
    self.daq_socket.stop()
    self.pull_socket.stop()

    time.sleep(0.1)  # Sleep 100ms for output to be complete
    return rocv2.from_raw(f'{remote_dir}/{remote_name}0.raw')

  def tbssh_command(self, cmd):
    """
    @brief Passing a command to tileboard tester to be executed.

    @details The stdout/stderr reading ensures that that command has properly
    finished before releasing thread resources. Here we assume that the command
    can be terminated without any inputs. The return will be the contents of
    stdout and stderr of requested command, each as singular strings.
    """
    sshin, sshout, ssherr = self.ssh_control.exec_command(cmd)
    return ('\n'.join([x for x in sshout.readlines()]),  #
            '\n'.join([x for x in ssherr.readlines()]))

  @staticmethod
  def deep_merge(dest, update, path=None):
    """
    @brief Updating a deeply nested dictionary-like object "dest" in-place using
    an update dictionary

    @details Updating the nested structure stored in the dictionary. The answer
    is adapted from this [answer][solution] on StackOverflow, except at because
    YAML configurations are not strictly dictionaries, we change the method of
    detecting nested structure to anything having the `__getitem__` method.

    [solution]:
    https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries/7205107#7205107
    """
    if path is None:  # Leaving default argument as empty mutable is dangerous!
      path = []
    for key in update:
      if key in dest:
        dest_is_nested = hasattr(dest[key], '__getitem__')
        up_is_nested = hasattr(update[key], '__getitem__')
        if dest_is_nested and up_is_nested:
          # If both are nested recursively update nested structure
          TBController.deep_merge(dest[key], update[key], path + [str(key)])
        elif not dest_is_nested and not up_is_nested:
          # If neither are nested update value directory
          dest[key] = update[key]
        else:
          # Otherwise there is a structure mismatch
          raise ValueError('Mismatch structure at %s'.format(
              '.'.join(path + [str(key)])))
      else:
        dest[key] = update[key]
    return dest

  @staticmethod
  def make_deep(*args):
    """
    @brief Short hand function for making a deeply nested dictionary entry

    @details As YAML configurations are typically represented as nested
    dictionary entries, to set a single parameter configuration will be very
    verbose to declare in vanilla python, like  `{'a': {'b':{'c':{'d':v}}}}`,
    which is difficult to read and format using typical tools. This method takes
    arbitrary number of arguments, with all entries except for the last to be
    used as a key to a dictionary. So the example given above would be declared
    using this function as `make_deep('a','b','c','d', v)`
    """
    if len(args) == 1:
      return args[0]
    else:
      return {args[0]: TBController.make_deep(*args[1:])}


class ZMQController:
  """
  @brief Common ZQM client class

  @details Generic controller interface to allow passing of information to and
  from the tileboard through a network connection (typically called a "socket").
  A controller instance will also always have an accompanying YAML configuration
  payload to be modified and passed to the main server socket. As with the
  typical setup routines defined for the other readout system.
  """
  def __init__(self):
    """
    @brief Setting up the required data member with None and do nothing more

    @details Construction of the connection should not be performed in the
    `init` method.
    """
    self.ip = None
    self.port = None
    self.socket = None
    self.yaml_config = None

  def init(self, ip=None, port=None, config_file='configs/init.yaml'):
    """
    @brief Starting the connection, and resetting the stored configuration.

    @details In the case that the socket is already connect, we also setup of
    the socket to be closed, then reconnect, so this function effectively
    functions as a reconnect method.
    """
    if self.socket is not None:
      self.socket.close()

    # Saving and resettting the zmq socket connection.
    self.ip = ip if ip is not None else self.ip
    self.port = port if port is not None else self.port
    self.socket = zmq.Context().socket(zmq.REQ)
    self.socket.connect("tcp://" + str(self.ip) + ":" + str(self.port))

    # Scrapping the existing yaml config with the specified file.
    with open(config_file) as fin:
      self.yaml_config = yaml.safe_load(fin)

  def socket_send(self, message: str) -> str:
    """
    @brief Sending a message over the socket connection and returning the
    respond string.

    @details This is the most common socket connect/respond pattern used in the
    subsequent classes. This method will is implemented to be "dumb": no
    additional parsing of the string will be carried out, as that will depend on
    the task that the specialized function wants to perform.
    """
    self.socket.send_string(message)
    return self.socket.recv()

  def socket_check(self, message: str, check_str: str) -> bool:
    """
    @brief Checking the response string on a message request for a particular
    substring.

    @details Send a message over the socket, then check the return string for
    the existence of the specified input token. Returns True if the token
    exists, False otherwise. This the second most common routine for checking if
    the target server is ready for some additional operation.
    """
    # Using the str.find method (return -1 if substring was not found)
    return self.socket_send(message).decode().lower().find(
        check_str.lower()) >= 0

  def configure(self, yaml_config: dict = None) -> str:
    """
    @brief Sending a yaml config string to socket connection.

    @details The return function will be the results of sending the
    configuration. If no YAML fragment is specified, then the entire
    configuration stored in the class instance is sent (this is potentially
    slow!). If a YAML configuration fragment is specified, then the
    configuration updated in the main configuration instances as well.
    """
    if not self.socket_check('configure', 'ready'):
      raise RuntimeError('Socket is not ready for configuration!')

    if yaml_config is None:
      yaml_config = self.yaml_config
    else:
      TBController.deep_merge(self.yaml_config, yaml_config)
    return self.socket_send(yaml.dump(yaml_config))


class I2CController(ZMQController):
  """
  @ingroup hardware

  @brief Specialized ZMQController class for I2C slow controls

  @details Changing the ZMQ request corresponding to I2C slow control
  instructions or I2C readout request to be a concrete and human readable function
  call.
  """
  def __init__(self):
    # """Additional attribute: Masking by detector ID"""
    super().__init__()
    # Not sure when this is needed. not adding for the time being.
    # self.maskedDetIds = []

  def init(self, ip=None, port=None, config_file='configs/init.yaml'):
    """
    @brief Initializing the slow controls socket

    @details Aside from the nominal routine, we also flush the current
    configuration into to the I2C server for completeness, as well as perform
    additional actions to set up the slow control IO directions.
    """
    super().init(ip=ip, port=port, config_file=config_file)

    if not self.socket_check('initialize', 'ready'):
      raise RuntimeError("""I2C server did receive a ready signal! Make sure the
                         I2C slow control server has been started without error
                         on the tileboard""")
    conf_msg = self.socket_send(yaml.dump(self.yaml_config))

    ## GPIO Settings
    self.set_gbtsca_gpio_direction(0x0fffff9C)  # '0': input, '1': output

    # enable (1) MPPC_BIAS1 (GPIO20), disable (0) MPPC_BIAS2 (GPIO21)
    self.set_gbtsca_gpio_vals(0x01 << 20, 0x11 << 20)

    # global enable LED system: LED_ON_OFF ('1': LED system ON), GPIO7:
    self.set_gbtsca_gpio_vals(0x1 << 7, 0x1 << 7)

    # put LED_DISABLE1 and LED_DISABLE2 to '0' ('0': LED system ON), GPIOs 8-15
    self.set_gbtsca_gpio_vals(0x00000000, 0b11111111 << 8)

  def reset_tdc(self):
    """Resetting the TDC settings"""
    return yaml.safe_load(self.socket_send("resettdc"))

  def cont_i2c(self, target, *vals):
    """
    A typical pattern for either getting or setting I2C values is done by
    sending the a "set/read_<target> <val1> <val2>" request string to the I2C
    server, where values indicate the target channel/sub-channels or user input
    values. Here we provide a simple interface to generate the expression of
    interest.
    """
    return self.socket_send(' '.join([target, *[str(x) for x in vals]]))

  """
  Defining the concrete I2C operations pairs
  """

  def get_sipm_voltage(self):
    return self.cont_i2c('read_sipm_voltage')

  def get_sipm_current(self):
    return self.cont_i2c('read_sipm_current')

  def get_led_voltage(self):
    return self.cont_i2c('read_led_voltage')

  def get_led_current(self):
    return self.cont_i2c('read_led_current')

  def set_led_dac(self, val):
    return self.cont_i2c('set_led_dac', val)

  def set_gbtsca_dac(self, dac, val):
    return self.cont_i2c('set_gbtsca_dac', dac, val)

  def read_gbtsca_dac(self, dac):
    return self.cont_i2c('read_gbtsca_dac', dac)

  def read_gbtsca_adc(self, channel):
    return self.cont_i2c('read_gbtsca_adc', channel)

  def read_gbtsca_gpio(self):
    return self.cont_i2c('read_gbtsca_gpio')

  def set_gbtsca_gpio_direction(self, direction):
    return self.cont_i2c('set_gbtsca_gpio_direction', direction)

  def get_gbtsca_gpio_direction(self):
    return self.cont_i2c('get_gbtsca_gpio_direction')

  def set_gbtsca_gpio_vals(self, vals, mask):
    return self.cont_i2c('set_gbtsca_gpio_vals', vals, mask)

  """
  Event more human readable formats for ADC value
  """

  def MPPC_Bias(self, channel=1) -> float:
    """Reading out the SiPM bias voltage in units of Volts"""
    adc_val = self.read_gbtsca_adc(9 if channel == 1 else 10)
    # Additional multiplier for resistor divider changes between different in
    # tileboard version TODO: update when TB version 2 or version 3 is received.
    ad_mult = (82. / 1.) / (200. / 4.)
    return float(adc_val) / 4095 * 204000 / 4000 * ad_mult


class DAQController(ZMQController):
  """
  @ingroup hardware

  @brief Specialization for the fast control and readout socket instances.

  @details Mainly for abstracting fast control settings to a human friendly
  function call.
  """
  def start(self):
    """Starting a config file control sequence"""
    while not self.socket_check('start', 'running'):
      time.sleep(0.1)

  def is_complete(self):
    """Checking whether then run sequence is complete"""
    return not self.socket_check('run_done', 'notdone')

  def stop(self):
    """Ensuring the the signal has been stopped"""
    return self.socket_send('stop')

  @staticmethod
  def update_yaml_node(yaml_node, mapping_dict, **kwargs):
    """
    @brief Simplified interface for updating a YAML node

    @details Short hand method for updating a YAML node using keyword arguments.
    The input expects the YAML key as the key for the mapping_dict key, while
    the value of the mapping_dict should be a length 2 tuple, with the first
    entry being the corresponding kwargs string-key, while the second entry is
    the default value to use should the keyword argument not be explicitly set.
    """
    for key, value in mapping_dict.items():
      yaml_node[key] = kwargs.get(value[0], value[1])

  def enable_fast_commands(self, **kwargs):
    """Setting up the fast acquisition settings"""
    DAQController.update_yaml_node(
        self.yaml_config['daq']['l1a_enables'], {
            'periodic_l1a_A': ('A', 0),
            'periodic_l1a_B': ('B', 0),
            'periodic_l1a_C': ('C', 0),
            'periodic_l1a_D': ('D', 0),
            'random_l1a': ('random', 0),
            'external_l1a': ('external', 0),
            'block_sequencer': ('sequencer', 0),
            'periodic_ancillary': ('ancillary', 0)
        }, **kwargs)

  def l1a_generator_settings(self,
                             name='A',
                             BX=0x10,
                             length=43,
                             cmdtype='L1A',
                             prescale=0,
                             followMode='DISABLE'):
    """Setting up L1 acquisition generator"""
    for gen in self.yaml_config['daq']['l1a_generator_settings']:
      if gen['name'] == name:
        gen['BX'] = BX
        gen['length'] = length
        gen['type'] = cmdtype
        gen['prescale'] = prescale
        gen['followMode'] = followMode

  def l1a_settings(self, **kwargs):
    """Updating the L1 acquisition information"""
    DAQController.update_yaml_node(
        self.yaml_config['daq']['l1a_settings'], {
            'bx_spacing': ('bx_spacing', 43),
            'external_debounced': ('external_debounced', 0),
            'length': ('length', 43),
            'ext_delay': ('ext_delay', 0),
            'prescale': ('prescale', 0),
            'log_rand_bx_period': ('log_rand_bx_period', 0),
        }, **kwargs)


# Unit test of Tileboard controller.
# Using a mock pedestal run as an example.
def test1():
  tbc = TBController()
  # Obtain these numbers from the server start up instance.
  tbc.init('10.42.0.63',
           daq_port=6000,
           cli_port=6001,
           i2c_port=5555,
           ssh_key=os.environ['HOME'] + '/.ssh/id_rsa',
           config_file='cfg/tbc_yaml/roc_config_ConvGain4.yaml')

  print(tbc.i2c_socket.MPPC_Bias())

  # Additional settings for the data acquisition fast controls
  tbc.daq_socket.enable_fast_commands(random=1)
  tbc.daq_socket.l1a_settings(bx_spacing=45)
  #
  arr = ak.concatenate([tbc.acquire(1000), tbc.acquire(1000)])

  print(arr[0:10].to_list())
  print(len(arr))


if __name__ == '__main__':
  test1()
