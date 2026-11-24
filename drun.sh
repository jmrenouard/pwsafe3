#!/bin/sh
set -eu

# Build the Fedora + Crypt::PWSafe3 image and run conversion using quoted host paths/args.
docker build -t psafe3 .
docker run --rm --user "$(id -u):$(id -g)" -e PWSAFE3_PASSWORD -v "$(pwd):/data" psafe3 "$@"
