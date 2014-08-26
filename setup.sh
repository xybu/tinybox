#!/bin/bash

sudo apt-get install cgroup-bin
mount -t cgroup none /sys/fs/cgroup
