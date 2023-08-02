#!/bin/bash

EXTERNAL_PATH=$(dirname $(realpath ${BASH_SOURCE[0]}))
cd $EXTERNAL_PATH

### External packages -- DRS4
wget https://www.psi.ch/sites/default/files/import/drs/SoftwareDownloadEN/drs-5.0.5.tar.gz
tar zxf drs-5.0.5.tar.gz
mkdir -p ${EXTERNAL_PATH}/drs
mv drs-5.0.5/* ${EXTERNAL_PATH}/drs/
rm drs-5.0.5.tar.gz

### External packages --- hexactrl-sw components
git archive --remote=ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/hexactrl-sw.git ROCv3 | tar xvf - sources/common/include/HGCROCv2RawData.h --directory=/tmp
mkdir -p ${EXTERNAL_PATH}/hexactrl-sw/
mv sources/common/include/HGCROCv2RawData.h ${EXTERNAL_PATH}/hexactrl-sw
rm sources/ -rf

# TODO: currenly picoscope only supports ARMv7.
#
# We shall not use ARMv7, as this makes python package management very difficult
# (neither pip nor conda ships with pre-compiled python packages on ARMv7, and
# archlinux-arm is the only known distribution to come with precompiled
# python-awkward). So the picoscope interface will be disabled until either
# PicoTech officially supports ARM64 or we find a way to easily cross compile on
# ARMv8.

# wget https://labs.picotech.com/debian/pool/main/libp/libps5000/libps5000_2.1.83-3r3073_amd64.deb   \
# ar x libps5000_2.1.83-3r3073_amd64.deb                                                             \
# tar xvf data.tar.xz ;
# mkdir -p ${EXTERNAL_PATH}/picocope                                                                 \
# mv  opt/picoscope/* /opt/external/picoscope                                                        \
# rm -rf control.tar.gz debian-binary;                                                               \
