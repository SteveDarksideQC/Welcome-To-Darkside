#!/usr/bin/env bash
if [ "$EUID" -ne 0 ]; then echo "Error: Run as root"; exit 1; fi

JOB=$1

case $JOB in
    "fix_nvidia_suspend")
        echo "options nvidia NVreg_PreserveVideoMemoryAllocations=1" > /etc/modprobe.d/99-darkside-nvidia-power.conf
        systemctl enable nvidia-suspend nvidia-hibernate nvidia-resume
        update-initramfs -u
        ;;
    "fix_nvidia_flicker")
        echo "options nvidia-drm modeset=1" > /etc/modprobe.d/99-darkside-nvidia-drm.conf
        update-initramfs -u
        ;;
    "fix_wayland")
        sed -i 's/#WaylandEnable=false/WaylandEnable=false/' /etc/gdm3/custom.conf
        systemctl restart gdm3 || true
        ;;
    "fix_nvidia_conflict")
        apt-get purge -y "^nvidia-.*" "^libnvidia-.*"
        apt-get autoremove -y
        ;;
    "fix_amd_freeze")
        if ! grep -q "amdgpu.noretry=0" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&amdgpu.noretry=0 /' /etc/default/grub
            update-grub
        fi
        ;;
    "fix_amd_performance")
        if ! grep -q "amdgpu.runpm=0" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&amdgpu.runpm=0 /' /etc/default/grub
            update-grub
        fi
        ;;
    "fix_rocm_discovery")
        usermod -aG video,render ${SUDO_USER:-$(logname)}
        echo 'SUBSYSTEM=="kfd", KERNEL=="kfd", TAG+="uaccess", GROUP="video"' > /etc/udev/rules.d/70-kfd.rules
        udevadm control --reload-rules && udevadm trigger
        ;;
    "fix_intel_artifacts")
        if ! grep -q "i915.enable_psr=0" /etc/default/grub; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&i915.enable_psr=0 /' /etc/default/grub
            update-grub
        fi
        ;;
    "fix_intel_power")
        echo "options i915 enable_fbc=1 enable_guc=3" > /etc/modprobe.d/99-darkside-intel.conf
        update-initramfs -u
        ;;
    "rebuild_dkms")
        apt-get install --reinstall -y dkms
        ;;
    "update_initramfs")
        update-initramfs -u -k all
        ;;
    "remove_kernels")
        apt-get autoremove --purge -y
        ;;
    "update_grub")
        update-grub
        ;;
    "show_grub")
        sed -i 's/GRUB_TIMEOUT_STYLE=hidden/GRUB_TIMEOUT_STYLE=menu/' /etc/default/grub
        sed -i 's/GRUB_TIMEOUT=0/GRUB_TIMEOUT=5/' /etc/default/grub
        update-grub
        ;;
    "hide_grub")
        sed -i 's/GRUB_TIMEOUT_STYLE=menu/GRUB_TIMEOUT_STYLE=hidden/' /etc/default/grub
        sed -i 's/GRUB_TIMEOUT=5/GRUB_TIMEOUT=0/' /etc/default/grub
        update-grub
        ;;
    "fix_grub_delay")
        if ! grep -q "GRUB_RECORDFAIL_TIMEOUT" /etc/default/grub; then
            echo "GRUB_RECORDFAIL_TIMEOUT=0" >> /etc/default/grub
        else
            sed -i 's/GRUB_RECORDFAIL_TIMEOUT=.*/GRUB_RECORDFAIL_TIMEOUT=0/' /etc/default/grub
        fi
        update-grub
        ;;
    "fix_broken")
        dpkg --configure -a && apt-get install -f -y
        ;;
    "fix_updates")
        rm -rf /var/lib/apt/lists/*
        apt-get update -y
        ;;
    "fix_network")
        systemctl restart NetworkManager
        ;;
    "fix_bluetooth")
        rfkill unblock bluetooth
        systemctl restart bluetooth
        ;;
    "fix_time_sync")
        timedatectl set-local-rtc 1 --adjust-system-clock
        ;;
    "update_pciids")
        update-pciids
        ;;
    "clean_cache")
        apt-get clean && apt-get autoremove -y
        journalctl --vacuum-time=3d
        ;;
    "hardware_swap")
        NEXT_GPU=$2
        echo "Initiating Hardware Swap Protocol..."
        
        # STEP 1: Purge NVIDIA if it currently exists
        if dpkg -l | grep -q "^ii  nvidia-driver"; then
            apt-get purge -y "^nvidia-.*" "^libnvidia-.*"
            rm -f /etc/modprobe.d/99-darkside-nvidia-power.conf
            rm -f /etc/modprobe.d/99-darkside-nvidia-drm.conf
        fi

        # STEP 2: Prep for the NEW card dynamically
        if [ "$NEXT_GPU" == "nvidia_open" ]; then
            add-apt-repository ppa:graphics-drivers/ppa -y
            apt-get update -y
            LATEST_OPEN=$(apt-cache pkgnames | grep -E '^nvidia-driver-[0-9]+-open$' | sort -V | tail -n 1)
            if [ -n "$LATEST_OPEN" ]; then
                apt-get install -y "$LATEST_OPEN" "${LATEST_OPEN/-driver-/-dkms-}"
            fi
        elif [ "$NEXT_GPU" == "nvidia_prop" ]; then
            add-apt-repository ppa:graphics-drivers/ppa -y
            apt-get update -y
            LATEST_PROP=$(apt-cache pkgnames | grep -E '^nvidia-driver-[0-9]+$' | sort -V | tail -n 1)
            if [ -n "$LATEST_PROP" ]; then
                apt-get install -y "$LATEST_PROP"
            fi
        elif [ "$NEXT_GPU" == "amd_intel" ]; then
            apt-get purge -y "rocm-*" || true
            sed -i 's/amdgpu.noretry=0 //g' /etc/default/grub
            sed -i 's/amdgpu.runpm=0 //g' /etc/default/grub
            sed -i 's/i915.enable_psr=0 //g' /etc/default/grub
        fi

        # STEP 3: Finalize and Shutdown
        update-grub
        update-initramfs -u -k all
        apt-get autoremove -y
        
        sleep 3
        shutdown -h now
        ;;
    *) echo "Unknown maintenance job: $JOB" ;;
esac
