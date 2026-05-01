#!/usr/bin/env bash

# Darkside OS Optimizer - Kernel Installation Engine

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root."
  exit 1
fi

JOB=$1
echo "Starting Kernel Engine Job: $JOB"

case $JOB in
    "install_liquorix")
        echo "Adding Liquorix PPA and installing Zen-tuned kernel..."
        add-apt-repository ppa:damentz/liquorix -y
        apt-get update -y
        apt-get install -y linux-image-liquorix-amd64 linux-headers-liquorix-amd64
        ;;
        
    "install_xanmod")
        echo "Importing XanMod GPG key and installing Edge kernel..."
        wget -qO - https://dl.xanmod.org/archive.key | gpg --dearmor -o /usr/share/keyrings/xanmod-archive-keyring.gpg --yes
        echo 'deb [signed-by=/usr/share/keyrings/xanmod-archive-keyring.gpg] http://deb.xanmod.org releases main' > /etc/apt/sources.list.d/xanmod-release.list
        apt-get update -y
        apt-get install -y linux-xanmod-edge
        ;;
        
    "build_tkg")
        echo "Preparing linux-tkg Auto-Compiler..."
        apt-get install -y git build-essential flex bison dwarves libssl-dev libelf-dev
        
        # Clean up old builds if they exist
        rm -rf /tmp/darkside-tkg
        mkdir -p /tmp/darkside-tkg
        cd /tmp/darkside-tkg
        
        echo "Cloning linux-tkg repository..."
        git clone https://github.com/Frogging-Family/linux-tkg.git
        cd linux-tkg
        
        echo "Injecting Darkside Custom Configuration (BORE, 1000Hz, Native CPU)..."
        cat << 'CFG' > customization.cfg
_cpusched="bore"
_compiler="gcc"
_processor_opt="native"
_timer_freq="1000"
_tickless="3"
_mitigations="false"
CFG

        echo "Starting compilation (This will take a while based on your CPU)..."
        # Bypasses the interactive prompts and forces the install
        yes "" | ./install.sh install
        ;;
        
    *)
        echo "Unknown kernel job."
        exit 1
        ;;
esac

echo "Kernel Job $JOB completed. Please reboot to apply."
