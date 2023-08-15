import ctlcmd.cmdbase as cmdbase
import time
#import ctypes


class drsset(cmdbase.controlcmd):
  """@brief Setting DRS4 readout operation parameters"""
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--triggerchannel',
                             type=int,
                             help="""
                             Index representing which channel to trigger on.""")
    self.parser.add_argument('--triggerdirection',
                             type=int,
                             help="""
                             Index representing the direction of the trigger. See
                             the outputs of "get --drs" for the available
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
                             nanoseconds""")

    # Data collection settings
    self.parser.add_argument('--samplerate',
                             type=float,
                             help="""
                             Sample rate, in units of GHz. Note that thi value
                             will be rounded to the closest clock rate available.
                             use get --drs to get the true sample rate""")
    self.parser.add_argument('--samples',
                             type=int,
                             default=1024,
                             help="""
                             Number of samples to collect after trigger cell""")

  def set_trigger(self, args):
    ## Getting default values if settings do not exists
    if not args.triggerchannel:
      args.triggerchannel = self.drs.get_trigger_channel()
    if not args.triggerlevel:
      args.triggerlevel = self.drs.get_trigger_level()
    if not args.triggerdelay:
      args.triggerdelay = self.drs.get_trigger_delay()
    if not args.triggerdirection:
      args.triggerdirection = self.drs.get_trigger_direction()

    # End function if nothing has changed
    if (args.triggerchannel == self.drs.get_trigger_channel()
        and args.triggerlevel == self.drs.get_trigger_level()
        and args.triggerdelay == self.drs.get_trigger_delay()
        and args.triggerdirection == self.drs.get_trigger_direction()):
      return

    self.drs.set_trigger(args.triggerchannel, args.triggerlevel,
                         args.triggerdirection, args.triggerdelay)

  def set_collection(self, args):
    if args.samples != None:
      self.drs.set_samples(args.samples)
    if args.samplerate != None:
      self.drs.set_rate(args.samplerate)

  def run(self, args):
    self.set_trigger(args)
    self.set_collection(args)


class drscalib(cmdbase.controlcmd):
  """@brief Running the DRS calibration process."""
  """This function will confirm with the user where or not the DRS is in the
  correct configuration before continuing.
  """
  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--skipconfirm',
                             action='store_true',
                             help='Skipping the confirmation dialog')

  def run(self, args):
    if not args.skipconfirm:
      self.prompt_input("""
        Running the DRS calibration process, make sure all DRS inputs channels
        are disconnect before continuing. Type [COMPLETE] to continue""",
                        allowed=['COMPLETE'])
    self.drs.run_calibrations()


class drsrun(cmdbase.savefilecmd):
  """@brief Running the DRS stand alone waveform extraction"""
  ##TODO: make the save root file correct
  DEFAULT_SAVEFILE = 'drsrun_<TIMESTAMP>.txt'

  def __init__(self, cmd):
    cmdbase.controlcmd.__init__(self, cmd)

  def add_args(self):
    self.parser.add_argument('--numevents',
                             type=int,
                             default=1000,
                             help='Number of events to store')
    self.parser.add_argument('--dumpbuffer',
                             action='store_true',
                             help="""
                             Prints the last stored waveform on the screen in
                             human readable format""")
    self.parser.add_argument('--channel',
                             type=int,
                             default=0,
                             help='Channel to collect input from')
    self.parser.add_argument('--sum',
                             action='store_true',
                             help="""
                             Store the sum of the waveform values instead of
                             waveforms itself""")
    self.parser.add_argument('--waittrigger',
                             type=int,
                             default=0,
                             help="""
                             Maximum wait time for a single trigger fire, units
                             in (ms). Set to 0 for indefinite trigger wait.""")
    self.parser.add_argument('--intstart',
                             type=int,
                             default=0,
                             help="""
                             Time sample to start the summation window, set to -1
                             to start from begining""")
    self.parser.add_argument('--intstop',
                             type=int,
                             default=1024,
                             help="""
                             Time sample to stop the summation window, set to -1
                             to finish at end.""")
    self.parser.add_argument('--pedstart',
                             type=int,
                             default=0,
                             help="""
                             Time sample to start the pedestal average, set to
                             same as pedstop to ignore pedestal summation.""")
    self.parser.add_argument('--pedstop',
                             type=int,
                             default=0,
                             help="""
                             Time sample to stop the pedestal average, set to
                             same as pedstart ignore pedestal summation.""")

  def run(self, args):
    ## First line in file contains convertion information

    ##TODO: decide what to do with this vs the root file, add to root file or keep with txt file?
    if self.savefile.tell() == 0:
      self.savefile.write("{time} {bits} {adcval}\n".format(
          time=1.0 / self.drs.get_rate(), bits=4, adcval=0.1))
      self.savefile.flush()

    for _ in self.start_pbar(range(args.numevents)):
      self.drs.start_collect()
      tstart = time.time()
      while not self.drs.is_ready():
        self.check_handle()
        try:  ## For stand alone runs with external trigger
          self.gpio.pulse(10, 100)
        except:
          pass
        # Additional time parsing function. To force the function to not wait on
        # triggers indefinitely, useful for stand along testing.
        tnow = time.time()
        if args.waittrigger != 0 and (tnow - tstart) * 1000 > args.waittrigger:
          self.drs.force_stop()
          time.sleep(0.001)

      if not args.sum:
        line = self.drs.get_waveform(args.channel)
        self.savefile.write("{line}\n".format(line=line))
      else:
        line = self.drs.get_waveformsum(args.channel, args.intstart, args.intstop,
                                    args.pedstart, args.pedstop)
        self.savefile.write("{line}\n".format(line=line))

    if args.dumpbuffer:
      self.drs.dumpbuffer(args.channel)
