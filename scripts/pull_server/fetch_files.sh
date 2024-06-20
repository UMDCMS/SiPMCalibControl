#!/bin/bash

# Cloning the required repository
git clone ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/hexactrl-sw.git       -b ROCv3
git clone ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/hexactrl-script.git   -b ROCv3_Tileboardv2p1 hexactrl-sw/hexasctrl-script
git clone ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/hexactrl-analysis.git -b ROCv3               hexactrl-sw/hexactrl-script/analysis

# Pulling the docker file and patching requirements
cd hexactrl-sw
wget https://raw.githubusercontent.com/UMDCMS/SiPMCalibControl/master/scripts/pull_server/data_puller.dockerfile
wget https://raw.githubusercontent.com/UMDCMS/SiPMCalibControl/master/scripts/pull_server/CMakeLists.patch
wget https://raw.githubusercontent.com/UMDCMS/SiPMCalibControl/master/scripts/pull_server/run_docker.sh
chmod +x run_docker.sh