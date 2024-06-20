#!/bin/bash

docker buildx build  --network="host" --tag hexactrl-client --rm --load -f data_puller.dockerfile ./
docker run -it       --network="host" hexactrl-client:latest  /bin/bash $EXEC
