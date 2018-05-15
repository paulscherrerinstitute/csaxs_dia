#!/bin/bash
VERSION=1.1.0

# Build the docker image.
docker build --no-cache=true -t docker.psi.ch:5000/csaxs_dia .

# Push it to our repo.
docker tag docker.psi.ch:5000/csaxs_dia docker.psi.ch:5000/csaxs_dia:$VERSION
docker push docker.psi.ch:5000/csaxs_dia:$VERSION
docker push docker.psi.ch:5000/csaxs_dia
