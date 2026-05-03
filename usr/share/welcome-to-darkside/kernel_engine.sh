#!/usr/bin/env bash

# Darkside OS Optimizer - Kernel Installation Engine

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root."
  exit 1
fi

JOB=$1
REAL_USER=${SUDO_USER:-$(logname)}
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
        echo "Launching TKG Builder..."
        apt-get update -y
        apt-get install -y git build-essential flex bison dwarves libssl-dev libelf-dev
        
        TKG_DIR="/home/$REAL_USER/.local/share/darkside-tkg"
        
        # True Interactive Logic: No forced configs injected.
        TKG_CMD="
        if [ ! -d '$TKG_DIR' ]; then
            echo 'First run detected. Downloading linux-tkg...'
            mkdir -p ~/.local/share
            git clone https://github.com/Frogging-Family/linux-tkg.git '$TKG_DIR'
            cd '$TKG_DIR'
        else
            echo 'Existing TKG build environment found. Updating script...'
            cd '$TKG_DIR'
            git pull
        fi
        
        # This will now trigger the full interactive questionnaire on the first run!
        ./install.sh
        echo -e '\nPress Enter to close...'
        read
        "
        
        # Launching the interactive terminal
        if command -v gnome-terminal &> /dev/null; then
            sudo -u "$REAL_USER" gnome-terminal -- bash -c "$TKG_CMD"
        elif command -v konsole &> /dev/null; then
            sudo -u "$REAL_USER" konsole -e bash -c "$TKG_CMD"
        elif command -v x-terminal-emulator &> /dev/null; then
            sudo -u "$REAL_USER" x-terminal-emulator -e bash -c "$TKG_CMD"
        else
            echo "Error: No terminal emulator found to launch TKG builder."
        fi
        ;;
        
    *)
        echo "Unknown kernel job."
        exit 1
        ;;
esac

echo "Kernel Job $JOB completed. Please reboot to apply."
