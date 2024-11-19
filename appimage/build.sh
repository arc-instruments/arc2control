#!/bin/sh

DIR=$(realpath $(dirname "$0")/..)

cd $DIR
# pick up existing requirements
cp requirements.txt appimage/requirements.txt
# and also add the directory of arc2control
echo "${DIR}" >> appimage/requirements.txt

# build it with python-appimage
python-appimage build app -l manylinux_2_28_x86_64 -p 3.12 -n arc2control appimage

if [ -f appimage/requirements.txt ]; then
  rm appimage/requirements.txt
fi

cd -
