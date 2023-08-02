#!/bin/bash

if [ -z "$PLATFORM" ]; then
  PLATFORM="linux/arm64"
fi


docker buildx build  --network="host" --tag sipmcalib_control --platform ${PLATFORM} --rm --load ./

if [[ ! -z "DEVICES" ]]; then
  DEVICES="--privileged -v /sys:/sys" # Additional low-level devices
fi

if [ $# -eq 0 ]; then
   EXEC=""
else
   EXEC="-c ${@}"
fi

docker run -it                                                  \
       --network="host"                                         \
       --platform ${PLATFORM}                                   \
       --mount type=bind,source="${PWD}",target=/srv            \
       --mount type=bind,source="/tmp",target=/tmp              \
       --mount type=bind,source="${HOME}/.ssh",target=/srv/.ssh \
       ${DEVICES}                                               \
       sipmcalib_control:latest                                 \
       /bin/bash --init-file "/srv/.install.sh" $EXEC
