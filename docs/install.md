@page install Installation instructions

## Deploying the Calibration Control programs

The dependencies required to compile and run the program is handled by
[docker][docker] with the `Dockerfile` found at the root directory of the
project. This ensures that all deployments will run under the same set of
packages to avoid setup specific issues from entering production.

Additional device permission setup is still required for the various data
collection and control interface. The current configuration is designed to work
on a [Raspberry Pi 3B+][raspi] running a [ArchLinux ARMv8][archarm] host, though
any Linux-based ARMv8 system should work, as long as one can set up system
permissions and can install an up-to-date version of docker.

First, we clone the code repository and pull the remote dependencies. Notice
that because some external dependencies are hosted in private repositories
(which will prompt a login message), you will need to make sure you have
permission to download the files of interest.

```bash
git clone https://github.com/UMDCMS/SiPMCalibControl.git
cd SiPMCalibControl
./external/fetch_external.sh
```

### Setting up system permissions

Modify the `/boot/config.txt` file so that PWM and I2C interfaces are available:
add the following lines to the _after_ the kernel loading line:

```bash
dtoverlay=pwm-2chan
dtparam=i2c_arm=on
```

Next, we create new permission groups to avoid running the master program as
root. If you are testing this program on your personal machine, do **not** add
yourself to the `gpio` and `i2c` groups, as these devices are typically reserved
for temperature monitor and control system on typical computer laptop. Randomly
changing `i2c` and `gpio` value **will** damage your device.

```bash
groupadd -f -r pico
usermod -a -G pico ${USER}
groupadd -f -r drs
usermod -a -G drs ${USER}
## DO NOT ADD!! unless you are sure of what you are doing!
# groupadd -f -r gpio
# usermod -a -G gpio ${USER}
# groupadd -f -r i2c
# usermod -a -G i2c ${USER}
```

Then, copy the custom `udev` rules to expose device IDs to the various groups.

```bash
cp external/rules/pico.rules  /etc/udev/rules/
cp external/rules/drs.rules   /etc/udev/rules/
## DO NOT ADD unless you are sure of what you are doing!!
# cp external/rules/digi.rules  /etc/udev/rules/
```

Reboot the Raspberry Pi board to have everything take effect.

### Installing software and firmware for the tileboard controller

The tileboard controller used to communicate with the HGCAL systems run on a
standalone ELM machine running a full operating system. The UMD control system
communicates with this system over Ethernet, assuming that the various services
on the tileboard system is operating nominally. Requirements for the tileboard
controller are maintained by the broader HGCAL community, mainly by the
University of Minnesota. With most of the instructions found for their
[read-the-docs page][hgcal-quickstart].

To avoid out-of-date information, we will not be including software installation
instructions here, but rather the administrators will be responsible for
ensuring the software and firmware on the tileboard controller is up-to-date.
The 3 key pieces of software that is required for the main calibration control
sequence to work would include:

- The fast controls interaction server (usually named `zmq-server`)
- The fast data pulling "client" (usually named the `zmq-client`)
- The slow controls and readout server (usually named the `zmq_server`, notice
  the difference in hyphenation).

Turn-key solutions for starting/stopping the tileboard control software programs
are kept in the `scripts/tbcontroller` directory.

### Deploying the docker image

After permissions have been set. Navigate back to the code repository, then
build and run the docker image:

```bash
DEVICES=1 ./deploy.sh
```

The `DEVICES` flag is used to expose all device interfaces to the underlying
docker image. Do **not** include this flag unless you know what you are doing.
The first run of this program would be slow as it is generating the docker
image. Subsequent runs should only upload changes made by the user and recompile
the repository code if needed. For the initial setup from a clean install, the
docker image generating is expected to take about 40-50 minutes to fully
complete. Once the program is complete, you should be greeted with a bash
prompt, where you can execute the main program:

```bash
python3 control.py     # For starting interactive CLI
python3 gui_control.py # For starting GUI server
```

The bash session is kept for the sake of debugging the deployment environment.
If you know you want to start up straight into the CLI or the GUI, you can run
the `./deploy.sh` like:

```bash
./deploy.sh python3 control.py     # For directly starting the interactive CLI
# ./deploy.sh python3 gui_control.py # TODO: currently fails to exit nominally
```

You will automatically exit the docker image one you terminate the CLI/GUI
session.

## Deployment for software testing

Installation instructions above should works for all UNIX like system assuming
you can set up the various system permissions. If you are uncertain which
permissions you can safely set up on the local machine, the program should still
be run-able without any special permissions (but you will not be able to use any
of the interface).

To build a docker image and start the docker image.

```bash
# For mocking a x86 system
PLATFORM=linux/amd64 ./deploy.sh

# For mocking a aarch64 system
PLATFORM=linux/arm64 ./deploy.sh
```

For testing if the new code can run without issues on the target ARM platform
(RPi3), you will potentially need the
[`docker-buildx`+`qemu-user-static`][docker-multilib] package combination
installed for the image builder to work. Beware the cross-platform execution can
have significant performance penalties, in particular for code compilation. Also
notice that device interfaces is not guaranteed to work through cross-platform
docker images (not even the USB based devices). The construction of the docker
image on a local laptop will take about 40-50 minutes from a clean installation
on a Raspberry Pi.

Between testing different image types, you will need to clear the `cmake` cache
files and compiled binary:

```bash
./clean.sh
```

Using the provided `deploy.sh` script, the repository directory is mounted to
the docker image, so edits made outside the docker image will also be reflected
inside the docker image. While this does mean you can install dependencies on
the fly in the docker image session, such installation will not be persistent.
If you are certain that you need a new package. Consider modifying the
Dockerfile or change the dependency listing files, then restart the `deploy`
script.

## Contributing to the code

The main code base is hosted at this [GitHub repository][github]. Contact the
developers for the pull request if you have something you want to add into the
code base!

### Code organization

Documentations for control software development can be found in their various
directories:

- Documentation of the Hardware interfaces and other minimal dependency helper
  objects/functions can be found [here](@ref hardware). The `src` directory
  contains the C++ implemented classes, and the `cmod` directory contains the
  python objects along with the python bindings for the C++ classes.
- Documentation of the CLI interface can be found [here](@ref cli_design). Files for
  this is typically found in the `ctlcmd` directory.
- Documentation of the GUI interface can be found [here](@ref gui_design). Files for
  this is typically found in the `server` directory:
  - The server side code is found in the `server/sockets` directory.
  - The client side code is found in the `server/static/js` directory.
  - Styling file will likely not get their own documentation.

[github]: https://github.com/UMDCMS/SiPMCalibControl
[opencv]: https://opencv.org/releases/
[cmake]: https://cmake.org/download/
[pybind11]: https://pybind11.readthedocs.io/en/stable/
[numpy]: https://numpy.org/
[flasksocket]: https://flask-socketio.readthedocs.io/en/latest/
[scipy]: https://www.scipy.org/scipylib/index.html
[picoscope]: https://www.picotech.com/downloads/linux
[picoscope_mac]: https://www.picotech.com/downloads
[sass]: https://sass-lang.com/install
[picoscope_download]: https://labs.picotech.com/debian/pool/main/libp/libps5000/
[ads1x15]: https://github.com/adafruit/Adafruit_CircuitPython_ADS1x15
[raspi]: https://www.raspberrypi.org/products/raspberry-pi-3-model-b-plus/
[archarm]: https://archlinuxarm.org/about/downloads
[paramiko]: http://www.paramiko.org/
[brew]: https://brew.sh/
[pip]: https://pip.pypa.io/en/stable/
[drs]: https://www.psi.ch/en/drs/software-download
[drs4_download]: https://www.psi.ch/en/drs/software-download
[npm]: https://www.npmjs.com/
[python-zmq]: https://pyzmq.readthedocs.io/en/latest/
[python-uproot]: https://uproot.readthedocs.io/en/latest/
[python-yaml]: https://pyyaml.org/wiki/PyYAMLDocumentation
[hgcal-quickstart]: https://readthedocs.web.cern.ch/display/HGCELE/Tileboard+Tester+V2+Quick+Start+Guide
[docker]: https://docs.docker.com/
[docker-multilib]: https://docs.docker.com/build/building/multi-platform/
