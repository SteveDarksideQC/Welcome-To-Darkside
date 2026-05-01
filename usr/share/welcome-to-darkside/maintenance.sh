#!/usr/bin/env bash

# Darkside OS Optimizer - Maintenance Engine

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root."
  exit 1
fi

JOB=$1

echo "Starting System Maintenance Job: $JOB"

case $JOB in
    "fix_broken")
        dpkg --configure -a
        apt-get --fix-broken install -y
        ;;
    "fix_updates")
        rm -rf /var/lib/apt/lists/*
        apt-get clean
        apt-get update -y
        ;;
    "remove_kernels")
        echo "Purging old unused kernels to free up boot space..."
        apt-get autoremove --purge -y
        ;;
    "clean_cache")
        apt-get clean
        apt-get autoclean
        ;;
    "fix_network")
        systemctl restart NetworkManager
        systemctl restart systemd-resolved
        ;;
    "fix_wayland")
        sed -i 's/^#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf
        ;;
    "update_grub")
        echo "Updating GRUB configuration..."
        update-grub
        ;;
    "show_grub")
        echo "Enabling GRUB Boot Menu..."
        sed -i 's/GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/' /etc/default/grub
        sed -i 's/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' /etc/default/grub
        update-grub
        ;;
    "hide_grub")
        echo "Hiding GRUB Boot Menu..."
        sed -i 's/GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=hidden/' /etc/default/grub
        sed -i 's/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=0/' /etc/default/grub
        update-grub
        ;;
    "rebuild_dkms")
        echo "Rebuilding DKMS modules (NVIDIA/Wi-Fi) for all kernels..."
        dkms autoinstall
        ;;
    "update_initramfs")
        echo "Regenerating initramfs via Dracut for all kernels..."
        # The proper Ubuntu 26.04+ Dracut command to rebuild everything
        dracut --force --regenerate-all
        ;;
    *)
        echo "Unknown maintenance job."
        exit 1
        ;;
esac

echo "Maintenance Job $JOB completed successfully."
