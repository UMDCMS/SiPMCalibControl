import ctlcmd.cmdbase as cmdbase


class picoset(cmdbase.controlcmd):
  """@brief Setting picoscope operation parameters"""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--range',
                             type=int,
                             help="""
                             Voltage range by index, use command "get --pico" for
                             the list of available numbers, both channel will be
                             set to the same range index""")

    ## Trigger related settings
    self.parser.add_argument('--triggerchannel',
                             type=int,
                             help="""
                             Index representing which channel to trigger on. See
                             the outputs of "get --pico" for the available
                             numbers""")
    self.parser.add_argument('--triggerdirection',
                             type=int,
                             help="""
                             Index representing the direction of the trigger. See
                             the outputs of "get --pico" for the available
                             numbers""")
    self.parser.add_argument('--triggerlevel',
                             type=float,
                             help="""
                             Trigger level in mV. Note that the value will be
                             rounded to the closest corresponding ADC value.""")
    self.parser.add_argument('--triggerdelay',
                             type=int,
                             help="""
                             Delay between trigger and data acquisition, units in
                             10 time intervals (see the outputs of "get --pico"
                             to get time intervals in nanoseconds)""")
    self.parser.add_argument('--waittrigger',
                             type=int,
                             help="""
                             Maximum wait time for a single trigger fire, units
                             in (ms). Set to 0 for indefinite trigger wait.""")

    ## Data collection settings
    self.parser.add_argument('--presamples',
                             type=int,
                             help="""
                             Number of samples to collect before data collection
                             trigger (takes into account delay)""")
    self.parser.add_argument('--postsamples',
                             type=int,
                             help="""
                             Number of samples to collect after data collection
                             trigger (takes into account delay)""")
    self.parser.add_argument('--ncaptures',
                             type=int,
                             help="""
                             Number of triggered capture to perform in a single
                             block""")

  def run(self, args):
    self.set_range(args)
    self.set_trigger(args)
    self.set_blocks(args)

  def set_range(self, args):
    if args.range:
      self.pico.setrange(0, args.range)
      self.pico.setrange(1, args.range)

  def set_trigger(self, args):
    if args.triggerchannel == None:
      args.triggerchannel = self.pico.triggerchannel
    if args.triggerdirection == None:
      args.triggerdirection = self.pico.triggerdirection
    if args.triggerlevel == None:
      args.triggerlevel = self.pico.triggerlevel
    if args.triggerdelay == None:
      args.triggerdelay = self.pico.triggerdelay
    if args.waittrigger == None:
      args.waittrigger = self.pico.triggerwait
    self.pico.settrigger(args.triggerchannel, args.triggerdirection,
                         args.triggerlevel, args.triggerdelay, args.waittrigger)

  def set_blocks(self, args):
    if args.presamples == None:
      args.presamples = self.pico.presamples
    if args.postsamples == None:
      args.postsamples = self.pico.postsamples
    if args.ncaptures == None:
      args.ncaptures = self.pico.ncaptures
    if (args.presamples != self.pico.presamples
        or args.postsamples != self.pico.postsamples
        or args.ncaptures != self.pico.ncaptures):
      self.pico.setblocknums(args.ncaptures, args.postsamples, args.presamples)


class picorunblock(cmdbase.savefilecmd):
  """@brief Initiating a single run block instance."""
  """ This assumes that the program will finish without user intervention (no
  program fired triggering)
  """

  DEFAULT_SAVEFILE = 'picoblock_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--numblocks',
                             type=int,
                             default=1,
                             help='Number of rapid block acquisitions to run')
    self.parser.add_argument('--dumpbuffer',
                             action='store_true',
                             help='Dumping the buffer onto screen')
    self.parser.add_argument('--channel',
                             type=int,
                             default=0,
                             help='Channel to collect input from')
    self.parser.add_argument('--sum',
                             action='store_true',
                             help="""
                             Store the sum of the waveform values instead of
                             waveforms itself""")

  def run(self, args):
    ## First line in file contains convertion information
    if self.savefile.tell() == 0:
      self.savefile.write("{time} {bits} {adc}\n".format(
          time=self.pico.timeinterval,
          bits=2,
          adc=self.pico.adc2mv(args.channel, 256)))
      self.savefile.flush()

    for i in range(args.numblocks):
      self.update('Collecting block...[{0:5d}/{1:d}]'.format(
          i,
          args.numblocks,
      ))
      self.pico.startrapidblocks()

      while not self.pico.isready():
        self.check_handle()
        if self.gpio.gpio_status():
          self.gpio.pulse(int(self.pico.ncaptures / 10), 100)

      self.pico.flushbuffer()

      lines = [
          self.pico.waveformstr(args.channel, cap)
          for cap in range(self.pico.ncaptures)
      ]
      self.savefile.write("\n".join(lines))

    if args.dumpbuffer:
      self.pico.dumpbuffer()


class picorange(cmdbase.controlcmd):
  """@brief Automatically setting the voltage range of the picoscope based on a
  few set waveforms of data."""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--captures',
                             type=int,
                             default=500,
                             help='Number of captures for base the calculation')
    self.parser.add_argument('--channel',
                             type=int,
                             default=0,
                             help='Input channel to base the calculation')
    self.parser.add_argument('--rangeidx',
                             type=int,
                             help="""
                             Specifying the range index for the specific channel.
                             Leave empty if you want automatic determination.""")

  def run(self, args):
    # Setting the new number of block to run
    self.pico.setblocknums(args.captures, self.pico.postsamples,
                           self.pico.presamples)
    if args.rangeidx != None:
      self.pico.setrange(self.channel, self.rangeidx)
    else:
      while 1:
        self.pico.startrapidblocks()
        while not self.pico.isready():
          self.gpio.pulse(self.pico.ncaptures, 500)
        self.pico.flushbuffer()

        wmax = self.pico.waveformmax(args.channel)

        if wmax < 100 and self.pico.range > self.pico.rangemin():
          self.pico.setrange(args.channel, self.pico.range - 1)
        elif wmax > 200 and self.pico.range < self.pico.rangemax():
          self.pico.setrange(args.channel, self.pico.range + 1)
        else:
          break
