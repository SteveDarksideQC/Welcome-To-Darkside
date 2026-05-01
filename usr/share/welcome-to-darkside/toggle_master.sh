#!/usr/bin/env bash

if [ "$EUID" -ne 0 ]; then exit 1; fi
STATE=$1
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$DIR/toggle_tweak.sh" grub_tweaks "$STATE"
"$DIR/toggle_tweak.sh" max_map_count "$STATE"
"$DIR/toggle_tweak.sh" file_max "$STATE"
"$DIR/toggle_tweak.sh" swappiness "$STATE"
"$DIR/toggle_tweak.sh" nvme_scheduler "$STATE"
"$DIR/toggle_tweak.sh" tcp_bbr "$STATE"
"$DIR/toggle_tweak.sh" nmi_watchdog "$STATE"
"$DIR/toggle_tweak.sh" inotify_watches "$STATE"
