#!/bin/sh
docker build -t psafe3 .
docker run  -v $(pwd):/data -t psafe3 $@