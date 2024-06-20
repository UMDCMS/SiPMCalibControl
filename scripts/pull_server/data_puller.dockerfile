# Primary base image setup
FROM    ubuntu:23.04
WORKDIR /srv
SHELL ["/bin/bash", "-c"]

# Required packages
ARG MAKE_DEPS="cmake git g++ gcc wget"
ARG PKGS_DEPS="libboost-all-dev libyaml-cpp-dev python3 libpugixml-dev libbsd-dev pkg-config cppzmq-dev libzmq3-dev systemd"
ARG ROOT_DEPS="dpkg-dev binutils libx11-dev libxpm-dev libgnutls28-dev"
ARG PYTHON_DEPS="python3-pip python3-numpy liblapack3 libjpeg-dev zlib1g-dev"
# Standard update and official packages
RUN apt update; \
    apt-get -y install ${MAKE_DEPS} ${PKGS_DEPS} ${ROOT_DEPS} ${PYTHON_DEPS}


# Installing ROOT (as per official root instructions)
RUN wget https://root.cern/download/root_v6.28.04.Linux-ubuntu22-x86_64-gcc11.3.tar.gz; \
    tar -xzf root_v6.28.04.Linux-ubuntu22-x86_64-gcc11.3.tar.gz;                        \
    source root/bin/thisroot.sh
ENV ROOTSYS=/srv/root

## Compiling the client code (Not using git clone here, as hexactrl is in a private repository)
COPY ./ /srv/hexactrl-sw

RUN mkdir -p hexactrl-sw/build;                                                       \
    cd hexactrl-sw/build ;                                                            \
    patch -u -i ../CMakeLists.patch ../CMakeLists.txt;                                \
    cmake -DBUILD_CLIENT=ON ../ ; make; make install;                                 \
    patch -u -i ../requirements.patch /srv/hexactrl/hexactrl-script/requirements.txt; \
    python3 -m pip install --break-system-packages -r /srv/hexactrl-sw/hexactrl-script/requirements.txt
# Additional python paths to use
ENV PYTHONPATH=$PYTHONPATH:/srv/hexactrl-sw/hexactrl-script/analysis

