#!/usr/bin/env bash

# Darkside OS Optimizer - Timeshift Backend Setup
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root."
  exit 1
fi

apt update -y
FS_TYPE=$(findmnt -n -o FSTYPE /)

if [ "$FS_TYPE" = "btrfs" ]; then
    apt install -y timeshift grub-btrfs timeshift-autosnap-apt
    timeshift --btrfs
else
    apt install -y timeshift
    timeshift --rsync
fi

# Initialize config by running a quick check
timeshift --check

# Enforce strict snapshot limits to protect SSD/HDD space
CONFIG_FILE="/etc/timeshift/timeshift.json"
if [ -f "$CONFIG_FILE" ]; then
    sed -i 's/"count_monthly" : "[0-9]*"/"count_monthly" : "0"/' "$CONFIG_FILE"
    sed -i 's/"count_weekly" : "[0-9]*"/"count_weekly" : "0"/' "$CONFIG_FILE"
    sed -i 's/"count_daily" : "[0-9]*"/"count_daily" : "3"/' "$CONFIG_FILE"
    sed -i 's/"count_hourly" : "[0-9]*"/"count_hourly" : "0"/' "$CONFIG_FILE"
    sed -i 's/"count_boot" : "[0-9]*"/"count_boot" : "2"/' "$CONFIG_FILE"
fi

# Create the initial pre-tweak snapshot
timeshift --create --comments "Darkside Pre-Tweak Initial Backup"
