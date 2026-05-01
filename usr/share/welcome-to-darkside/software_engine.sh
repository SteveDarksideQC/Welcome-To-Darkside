#!/usr/bin/env bash
if [ "$EUID" -ne 0 ]; then echo "Error: Run as root"; exit 1; fi

JOB=$1
TARGET=$2

REAL_USER=${SUDO_USER:-$(logname)}

ensure_flatpak() {
    if ! command -v flatpak &> /dev/null; then
        apt-get update -y && apt-get install -y flatpak
        flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    fi
}

case $JOB in
    "resolve_install" | "resolve_update")
        ZIP_PATH=$TARGET
        if [ -z "$ZIP_PATH" ] || [ ! -f "$ZIP_PATH" ]; then echo "Invalid file"; exit 1; fi
        
        echo "Extracting $ZIP_PATH..."
        mkdir -p /tmp/resolve_installer
        unzip -o "$ZIP_PATH" -d /tmp/resolve_installer
        
        RUN_FILE=$(find /tmp/resolve_installer -name "*.run" | head -n 1)
        if [ -n "$RUN_FILE" ]; then
            chmod +x "$RUN_FILE"
            "$RUN_FILE" -i -y
        fi
        rm -rf /tmp/resolve_installer

        apt update -y
        apt install -y libapr1 libaprutil1 libxcb-composite0 libxcb-cursor0 libxcb-damage0 ocl-icd-libopencl1 rocm-opencl-icd

        RESOLVE_LIB="/opt/resolve/libs"
        if [ -d "$RESOLVE_LIB" ]; then
            mkdir -p "$RESOLVE_LIB/disabled-libraries"
            mv "$RESOLVE_LIB"/libglib-2.0.so* "$RESOLVE_LIB/disabled-libraries/" 2>/dev/null
            mv "$RESOLVE_LIB"/libgio-2.0.so* "$RESOLVE_LIB/disabled-libraries/" 2>/dev/null
            mv "$RESOLVE_LIB"/libgmodule-2.0.so* "$RESOLVE_LIB/disabled-libraries/" 2>/dev/null
        fi
        ;;
    "install_lact")
        LACT_URL=$(curl -s https://api.github.com/repos/ilya-zlobintsev/LACT/releases/latest | grep "browser_download_url.*amd64.deb" | cut -d '"' -f 4 | head -n 1)
        if [ -n "$LACT_URL" ]; then
            wget -qO /tmp/lact.deb "$LACT_URL"
            apt install -y /tmp/lact.deb && rm /tmp/lact.deb
        fi
        if ! grep -q "amdgpu.ppfeaturemask=0xffffffff" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&amdgpu.ppfeaturemask=0xffffffff /' /etc/default/grub
            update-grub
        fi
        systemctl enable --now lactd
        ;;
    "obs_ultimate")
        ensure_flatpak
        flatpak install -y flathub com.obsproject.Studio com.obsproject.Studio.Plugin.BackgroundRemoval com.obsproject.Studio.Plugin.Gstreamer com.obsproject.Studio.Plugin.OBSVkCapture
        ;;
    "virt_desktop_combo")
        apt update -y && apt install -y docker.io docker-compose git
        usermod -aG docker "$REAL_USER"
        ensure_flatpak && flatpak install -y flathub com.freerdp.FreeRDP
        su - "$REAL_USER" -c "if [ ! -d ~/Winboat ]; then git clone https://github.com/Winboat/Winboat.git ~/Winboat; fi"
        ;;
    "virt_manager")
        apt update -y && apt install -y virt-manager qemu-desktop libvirt-clients libvirt-daemon-system bridge-utils virtinst libvirt-daemon
        usermod -aG libvirt "$REAL_USER" && usermod -aG kvm "$REAL_USER"
        ;;
    "install_lamp")
        apt update -y && apt install -y apache2 mysql-server php libapache2-mod-php php-mysql
        ;;
    "install_gamedev")
        ensure_flatpak
        flatpak install -y flathub org.godotengine.Godot org.kde.krita org.blender.Blender
        ;;
    "install_emulators")
        ensure_flatpak
        flatpak install -y flathub org.libretro.RetroArch net.pcsx2.PCSX2 net.rpcs3.RPCS3 org.DolphinEmu.dolphin-emu
        ;;
    "install_streaming")
        ensure_flatpak
        flatpak install -y flathub com.obsproject.Studio org.audacityteam.Audacity com.github.wwmm.easyeffects com.core447.StreamController
        ;;
    "install_chrome")
        wget -qO /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
        apt install -y /tmp/chrome.deb && rm /tmp/chrome.deb
        ;;
    "install_edge")
        wget -qO /tmp/edge.deb https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_124.0.2478.80-1_amd64.deb
        apt install -y /tmp/edge.deb && rm /tmp/edge.deb
        ;;
    "install_brave")
        curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg
        echo "deb [signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main" | tee /etc/apt/sources.list.d/brave-browser-release.list
        apt update -y && apt install -y brave-browser
        ;;
    "install_thorium")
        wget -qO /tmp/thorium.deb https://github.com/Alex31303/thorium/releases/download/M124.0.6367.218/thorium-browser_124.0.6367.218_amd64.deb
        apt install -y /tmp/thorium.deb && rm /tmp/thorium.deb
        ;;
    "install_steam")
        dpkg --add-architecture i386 && apt update -y
        apt install -y steam-installer || apt install -y steam
        ;;
    *)
        if [[ $JOB == "fp:"* ]]; then
            ensure_flatpak && flatpak install -y flathub ${JOB#fp:}
        else
            apt-get update -y && apt-get install -y $JOB
        fi
        ;;
esac
