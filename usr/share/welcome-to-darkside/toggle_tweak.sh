#!/usr/bin/env bash

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root."
  exit 1
fi

TWEAK_NAME=$1
STATE=$2

# 1. Max Map Count
if [ "$TWEAK_NAME" = "max_map_count" ]; then
    CONF_FILE="/etc/sysctl.d/99-darkside-maxmap.conf"
    if [ "$STATE" = "on" ]; then echo "vm.max_map_count=2147483642" > "$CONF_FILE"; else rm -f "$CONF_FILE"; sysctl -w vm.max_map_count=65530; fi
    sysctl --system
fi

# 2. File Max
if [ "$TWEAK_NAME" = "file_max" ]; then
    CONF_FILE="/etc/sysctl.d/99-darkside-filemax.conf"
    if [ "$STATE" = "on" ]; then echo "fs.file-max=524288" > "$CONF_FILE"; else rm -f "$CONF_FILE"; sysctl -w fs.file-max=9223372036854775807; fi
    sysctl --system
fi

# 3. Swappiness
if [ "$TWEAK_NAME" = "swappiness" ]; then
    CONF_FILE="/etc/sysctl.d/99-darkside-swappiness.conf"
    if [ "$STATE" = "on" ]; then echo "vm.swappiness=10" > "$CONF_FILE"; else rm -f "$CONF_FILE"; sysctl -w vm.swappiness=60; fi
    sysctl --system
fi

# 4. NVMe Scheduler
if [ "$TWEAK_NAME" = "nvme_scheduler" ]; then
    RULE_FILE="/etc/udev/rules.d/99-darkside-nvme.rules"
    if [ "$STATE" = "on" ]; then echo 'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"' > "$RULE_FILE"; else rm -f "$RULE_FILE"; fi
    udevadm control --reload-rules && udevadm trigger
fi

# 5. GRUB Tweaks
if [ "$TWEAK_NAME" = "grub_tweaks" ]; then
    GRUB_FILE="/etc/default/grub"
    PARAMS="preempt=full threadirqs mitigations=off amd_pstate=active"
    cp "$GRUB_FILE" "${GRUB_FILE}.darkside.bak"
    if [ "$STATE" = "on" ]; then
        if ! grep -q "preempt=full" "$GRUB_FILE"; then sed -i "s/GRUB_CMDLINE_LINUX_DEFAULT=\"[^\"]*/& $PARAMS/" "$GRUB_FILE"; update-grub; fi
    else
        sed -i "s/ $PARAMS//g" "$GRUB_FILE"; sed -i "s/$PARAMS//g" "$GRUB_FILE"; update-grub
    fi
fi

# 6. TCP BBR
if [ "$TWEAK_NAME" = "tcp_bbr" ]; then
    CONF_FILE="/etc/sysctl.d/99-darkside-bbr.conf"
    if [ "$STATE" = "on" ]; then 
        echo -e "net.core.default_qdisc=fq\nnet.ipv4.tcp_congestion_control=bbr" > "$CONF_FILE"
    else 
        rm -f "$CONF_FILE"; sysctl -w net.ipv4.tcp_congestion_control=cubic; sysctl -w net.core.default_qdisc=fq_codel
    fi
    sysctl --system
fi

# 7. Disable NMI Watchdog
if [ "$TWEAK_NAME" = "nmi_watchdog" ]; then
    CONF_FILE="/etc/sysctl.d/99-darkside-watchdog.conf"
    if [ "$STATE" = "on" ]; then echo "kernel.nmi_watchdog=0" > "$CONF_FILE"; else rm -f "$CONF_FILE"; sysctl -w kernel.nmi_watchdog=1; fi
    sysctl --system
fi

# 8. Inotify Max Watches
if [ "$TWEAK_NAME" = "inotify_watches" ]; then
    CONF_FILE="/etc/sysctl.d/99-darkside-inotify.conf"
    if [ "$STATE" = "on" ]; then echo "fs.inotify.max_user_watches=524288" > "$CONF_FILE"; else rm -f "$CONF_FILE"; sysctl -w fs.inotify.max_user_watches=65536; fi
    sysctl --system
fi
