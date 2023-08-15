"""
@file digicmd.py

@brief Commands for raw control and display of GPIO/ADC/PWM related interfaces
functions

"""
import ctlcmd.cmdbase as cmdbase
import time


class pulse(cmdbase.controlcmd):
  """
  Running the trigger for a certain about of pulses with alternative wait
  options.

  @details this is some test
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('-n',
                             type=int,
                             default=100000,
                             help='number of times to fire the trigger')
    self.parser.add_argument('--wait',
                             type=int,
                             default=500,
                             help='Time (in microseconds) between triggers')

  def run(self, args):
    # Splitting into 1000 chunks
    for i in range(args.n // 100):
      self.check_handle()
      self.client.gpio.pulse(100, args.wait)


class pwm(cmdbase.controlcmd):
  """
  Changing the pwm duty cycle and frequency
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--channel',
                             '-c',
                             type=int,
                             choices=[0, 1],
                             required=True,
                             help='PWM channel to alter')
    self.parser.add_argument('--duty',
                             '-d',
                             type=float,
                             required=True,
                             help='Duty cycle of the PWM')
    self.parser.add_argument('--frequency',
                             '-f',
                             type=float,
                             default=10000,
                             help='Base frequency of the PWM')

  def run(self, args):
    self.client.gpio.pwm(args.channel, args.duty, args.frequency)


class setadcref(cmdbase.controlcmd):
  """
  Setting the reference voltage of the ADC readout for temperature conversion
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--channel',
                             '-c',
                             type=int,
                             choices=[0, 1, 2, 3],
                             nargs='+',
                             help="""Channel to set reference voltage (can set
                             multiple to same value in a single command call)""")
    self.parser.add_argument('--val',
                             '-v',
                             type=float,
                             default=5000,
                             help="""
                             Reference voltage to specified channels (units: mV)
                             """)

  def run(self, args):
    for channel in args.channel:
      self.client.gpio.adc_setref(channel, args.val)


class showadc(cmdbase.controlcmd):
  """
  Printing the most recent readout values associated with ADC readouts.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, args):
    self.printdump('', [  #
        ('LED', f'{self.client.gpio.ntc_read(0):5.2f}C',
         f'{self.client.gpio.adc_read(0):5.1f}mV'),  #
        ('SiPM', f'{self.client.gpio.rtd_read(1):5.2f}C',
         f'{self.client.gpio.adc_read(1):5.1f}mV'),  #
        ('PWM0', '', f'{self.client.gpio.adc_read(2):6.1f}mV'),  #
        ('PWM1', '', f'{self.client.gpio.adc_read(3):6.1f}mV'),  #
    ])


class lighton(cmdbase.controlcmd):
  """@brief Turning the LED lights on."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, args):
    self.client.gpio.light_on()


class lightoff(cmdbase.controlcmd):
  """@brief Turning the LED lights off."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def run(self, line):
    self.client.gpio.light_off()
