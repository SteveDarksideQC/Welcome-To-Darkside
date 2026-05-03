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
        TARGET=$2
        echo "Initiating Hardware Swap Protocol: $TARGET..."
        
        # STEP 1: The Meta-Package Shield (Protect the Desktop from Autoremove)
        apt-mark manual gdm3 ubuntu-desktop linux-firmware sddm kubuntu-desktop 2>/dev/null || true

        # STEP 2: Clear Out Legacy X11 Configurations
        rm -f /etc/X11/xorg.conf
        rm -rf /etc/X11/xorg.conf.d/90-nvidia.conf
        rm -f /etc/modprobe.d/99-darkside-nvidia-power.conf
        rm -f /etc/modprobe.d/99-darkside-nvidia-drm.conf

        # STEP 3: Purge NVIDIA (If present)
        if dpkg -l | grep -q "^ii  nvidia-driver"; then
            apt-get purge -y "^nvidia-.*" "^libnvidia-.*"
        fi

        # STEP 4: Surgical GRUB Cleanup (Strips ONLY old GPU configs, leaves CPU configs intact)
        sed -i 's/ nvidia-drm.modeset=[0-9]//g' /etc/default/grub
        sed -i 's/ nvidia-drm.fbdev=[0-9]//g' /etc/default/grub
        sed -i 's/ nvidia.NVreg_EnableGpuFirmware=[0-9]//g' /etc/default/grub
        sed -i 's/ amdgpu.ppfeaturemask=[^ "]*//g' /etc/default/grub
        sed -i 's/  / /g' /etc/default/grub # Clean up any double spaces left behind

        # STEP 5: Prepare for the NEW card dynamically
        if [ "$TARGET" == "nvidia_5000" ]; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&nvidia-drm.modeset=1 nvidia-drm.fbdev=1 /' /etc/default/grub
            add-apt-repository ppa:graphics-drivers/ppa -y
            apt-get update -y
            LATEST_OPEN=$(apt-cache pkgnames | grep -E '^nvidia-driver-[0-9]+-open$' | sort -V | tail -n 1)
            if [ -n "$LATEST_OPEN" ]; then
                apt-get install -y "$LATEST_OPEN" "${LATEST_OPEN/-driver-/-dkms-}"
            fi

        elif [ "$TARGET" == "nvidia_legacy" ]; then
            sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_EnableGpuFirmware=1 /' /etc/default/grub
            add-apt-repository ppa:graphics-drivers/ppa -y
            apt-get update -y
            LATEST_PROP=$(apt-cache pkgnames | grep -E '^nvidia-driver-[0-9]+$' | sort -V | tail -n 1)
            if [ -n "$LATEST_PROP" ]; then
                apt-get install -y "$LATEST_PROP"
            fi

        elif [ "$TARGET" == "amd" ] || [ "$TARGET" == "intel" ]; then
            # Inject new parameters based on Open Source target
            if [ "$TARGET" == "amd" ]; then
                sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&amdgpu.ppfeaturemask=0xffffffff /' /etc/default/grub
            else
                # Intel specific check to inject iommu=pt if not present
                if ! grep -q "iommu=pt" /etc/default/grub; then
                    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/&iommu=pt /' /etc/default/grub
                fi
            fi

            # Clean out ROCm if present
            apt-get purge -y "rocm-*" || true

            # Pull Mesa drivers & 32-bit architecture for Open Source Gaming
            dpkg --add-architecture i386
            apt-get update -y
            apt-get install -y mesa-utils vulkan-tools libgl1-mesa-dri:i386 libgl1:i386 libglx-mesa0:i386 libvulkan1:i386 mesa-vulkan-drivers:i386

            # Force Flatpak to abandon isolated NVIDIA runtimes
            if command -v flatpak &> /dev/null; then
                echo "Scrubbing Flatpak sandbox of NVIDIA runtimes..."
                for rt in $(flatpak list --app-runtime 2>/dev/null | grep -i nvidia | awk '{print $2}'); do
                    flatpak uninstall -y "$rt"
                done
                flatpak uninstall --unused -y
                
                echo "Repairing Flatpak filesystem links..."
                flatpak repair
                
                echo "Updating remaining runtimes to pull Mesa..."
                flatpak update -y
            fi
        fi

        # STEP 6: Finalize, Rebuild Images, and Shutdown safely
        sed -i 's/  / /g' /etc/default/grub
        update-grub
        update-initramfs -u -k all
        apt-get autoremove -y
        
        sleep 3
        shutdown -h now
        ;;
    *) echo "Unknown maintenance job: $JOB" ;;
esac
