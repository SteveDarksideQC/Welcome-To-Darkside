import sys, os, subprocess, threading, platform, shutil, gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

_ = lambda s: s

USER_CONFIG_DIR = os.path.expanduser("~/.config/darkside-tweaks")
SAFETY_FLAG_FILE = os.path.join(USER_CONFIG_DIR, "safety_setup_done")

# --- DYNAMIC ICON GENERATOR ---
ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111111"/>
      <stop offset="100%" stop-color="#1a1a2e"/>
    </linearGradient>
    <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8a2be2"/>
      <stop offset="100%" stop-color="#e94560"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="120" fill="url(#g1)"/>
  <path d="M256 80 A 176 176 0 1 0 432 256 A 176 176 0 0 1 256 80 Z" fill="url(#g2)"/>
  <path d="M360 256 l30-20 l-15-45 l-35 10 l-25-25 l10-35 l-45-15 l-20 30 l-20-30 l-45 15 l10 35 l-25 25 l-35-10 l-15 45 l30 20 l-30 20 l15 45 l35-10 l25 25 l-10 35 l45 15 l20-30 l20 30 l45-15 l-10-35 l25-25 l35 10 l15-45 Z" fill="#0f3460" opacity="0.8"/>
  <circle cx="256" cy="256" r="60" fill="url(#g1)"/>
  <circle cx="256" cy="256" r="40" fill="url(#g2)"/>
</svg>"""

icon_dir = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
os.makedirs(icon_dir, exist_ok=True)
with open(os.path.join(icon_dir, "welcome-to-darkside.svg"), "w") as f:
    f.write(ICON_SVG)

def get_cpu_name():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'model name' in line: return line.split(':')[1].strip()
    except Exception: pass
    return "Unknown CPU"

def get_gpu_name():
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'VGA' in line or '3D' in line:
                parts = line.split(': ')
                if len(parts) > 1: return parts[-1].strip()
    except Exception: pass
    return "Unknown GPU"

def get_display_server():
    return os.environ.get('XDG_SESSION_TYPE', 'Unknown').capitalize()

def is_app_installed(apt_cmd=None, flatpak_id=None):
    if apt_cmd and shutil.which(apt_cmd): return True
    if flatpak_id:
        try:
            if subprocess.run(['flatpak', 'info', flatpak_id], capture_output=True).returncode == 0: return True
        except FileNotFoundError: pass
    return False

class DarksideWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Welcome to Darkside")
        self.set_default_size(1200, 850)
        os.makedirs(USER_CONFIG_DIR, exist_ok=True)
        self.is_task_running = False
        self.is_initializing_ui = True 
        self.child_switches = []
        self.theme_btns = []

        self.main_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.set_content(self.main_stack)

        self.build_safety_screen()
        self.build_dashboard_screen()

        if not os.path.exists(SAFETY_FLAG_FILE): self.main_stack.set_visible_child_name("safety_screen")
        else: self.main_stack.set_visible_child_name("dashboard_screen")
        self.is_initializing_ui = False

    def build_safety_screen(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Adw.HeaderBar())
        status_page = Adw.StatusPage(title="Welcome to Darkside", description="Configure Timeshift before unleashing extreme optimizations.", icon_name="security-high-symbolic")
        status_page.set_vexpand(True)
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, halign=Gtk.Align.CENTER, margin_bottom=50)
        self.progress_bar = Gtk.ProgressBar(visible=False, margin_bottom=10)
        self.progress_bar.set_size_request(300, -1)
        self.button_box.append(self.progress_bar)
        
        setup_btn = Gtk.Button(label="Setup Safety Net", css_classes=["suggested-action", "pill"])
        setup_btn.set_size_request(300, 50)
        setup_btn.connect("clicked", self.on_setup_safety_clicked)
        self.button_box.append(setup_btn)
        
        skip_btn = Gtk.Button(label="Skip (I like living dangerously)", css_classes=["destructive-action", "pill"])
        skip_btn.set_size_request(300, 40)
        skip_btn.connect("clicked", lambda b: self.main_stack.set_visible_child_name("dashboard_screen"))
        self.button_box.append(skip_btn)
        
        box.append(status_page)
        box.append(self.button_box)
        self.main_stack.add_named(box, "safety_screen")

    def build_dashboard_screen(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.view_stack = Adw.ViewStack()
        
        # --- 1: STATUS ---
        page1 = Adw.PreferencesPage()
        info_grp = Adw.PreferencesGroup(title="System Information")
        info_grp.add(Adw.ActionRow(title="Operating System", subtitle="Ubuntu 26.04+ Core"))
        info_grp.add(Adw.ActionRow(title="Active Kernel", subtitle=platform.release()))
        info_grp.add(Adw.ActionRow(title="Processor (CPU)", subtitle=get_cpu_name()))
        info_grp.add(Adw.ActionRow(title="Graphics (GPU)", subtitle=get_gpu_name()))
        info_grp.add(Adw.ActionRow(title="Display Server", subtitle=get_display_server()))
        page1.add(info_grp)
        
        tweak_grp = Adw.PreferencesGroup()
        self.expander = Adw.ExpanderRow(title="Core System Tweaks", subtitle="Aggressive hardware optimizations.")
        self.expander.set_expanded(True)
        self.master_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.master_switch.connect("notify::active", self.on_master_toggled)
        self.expander.add_suffix(self.master_switch)

        for t, s, idn, path in [
            ("Stock Kernel on Steroids", "Injects preempt=full", "grub_tweaks", "/etc/default/grub"),
            ("Force Max Map Count", "For modded games", "max_map_count", "/etc/sysctl.d/99-darkside-maxmap.conf"),
            ("Increase Open File Limits", "Boosts Esync", "file_max", "/etc/sysctl.d/99-darkside-filemax.conf"),
            ("Low Swappiness Profile (10)", "Prevents RAM dumping", "swappiness", "/etc/sysctl.d/99-darkside-swappiness.conf"),
            ("Bypass NVMe Schedulers", "Gen4/Gen5 optimization", "nvme_scheduler", "/etc/udev/rules.d/99-darkside-nvme.rules"),
            ("Enable TCP BBR", "Massively reduces network latency", "tcp_bbr", "/etc/sysctl.d/99-darkside-bbr.conf"),
            ("Disable NMI Watchdog", "Frees up raw CPU cycles", "nmi_watchdog", "/etc/sysctl.d/99-darkside-watchdog.conf"),
            ("Increase Inotify Watches", "Fixes Steam file limits", "inotify_watches", "/etc/sysctl.d/99-darkside-inotify.conf")
        ]:
            row = Adw.ActionRow(title=t, subtitle=s)
            switch = Gtk.Switch(valign=Gtk.Align.CENTER)
            switch.set_active(os.path.exists(path))
            switch.connect("notify::active", self.on_tweak_toggled, idn)
            row.add_suffix(switch)
            self.child_switches.append(switch)
            self.expander.add_row(row)
        
        tweak_grp.add(self.expander)
        page1.add(tweak_grp)
        self.view_stack.add_titled_with_icon(page1, "status", "Status", "computer-symbolic")

        # --- 2: KERNEL ---
        page_kernel = Adw.PreferencesPage()
        
        tkg_group = Adw.PreferencesGroup(title="TKG Custom Kernel Builder")
        tkg_row = Adw.ActionRow(title="Build and Install TKG Kernel", subtitle="Auto-injects BORE scheduler and 1000Hz timer.")
        tkg_btn = Gtk.Button(label="Build Kernel", valign=Gtk.Align.CENTER, css_classes=["suggested-action", "pill"])
        tkg_btn.connect("clicked", self.run_kernel_job, "build_tkg")
        tkg_row.add_suffix(tkg_btn)
        tkg_group.add(tkg_row)
        page_kernel.add(tkg_group)

        precomp_group = Adw.PreferencesGroup(title="Pre-Compiled Gaming Kernels")
        for title, sub, job in [("Install XanMod Edge Kernel", "Optimized for heavy desktop workloads.", "install_xanmod"), ("Install Liquorix Kernel", "Aggressive Zen interactivity scheduler.", "install_liquorix")]:
            row = Adw.ActionRow(title=title, subtitle=sub)
            btn = Gtk.Button(label="Install", valign=Gtk.Align.CENTER, css_classes=["pill"])
            btn.connect("clicked", self.run_kernel_job, job)
            row.add_suffix(btn)
            precomp_group.add(row)
        page_kernel.add(precomp_group)

        grub_group = Adw.PreferencesGroup(title="Bootloader Configuration")
        for title, sub, job in [("Update GRUB", "Scans for new kernels.", "update_grub"), ("Show Boot Menu", "Displays the GRUB menu.", "show_grub"), ("Hide Boot Menu", "Silent Fast Boot.", "hide_grub")]:
            row = Adw.ActionRow(title=title, subtitle=sub)
            btn = Gtk.Button(label="Run", valign=Gtk.Align.CENTER, css_classes=["pill"])
            btn.connect("clicked", self.run_maintenance_job, job, True)
            row.add_suffix(btn)
            grub_group.add(row)
        page_kernel.add(grub_group)
        
        kernel_maint_group = Adw.PreferencesGroup(title="Kernel Maintenance")
        for title, sub, job in [("Rebuild Kernel Modules (DKMS)", "Fixes NVIDIA or Wi-Fi drivers.", "rebuild_dkms"), ("Regenerate Initramfs (Dracut)", "Rebuilds Dracut images.", "update_initramfs"), ("Remove Old Kernels", "Purges outdated kernels.", "remove_kernels")]:
            kernel_maint_group.add(self.create_maintenance_group_row(title, sub, job, True))
        page_kernel.add(kernel_maint_group)

        self.view_stack.add_titled_with_icon(page_kernel, "kernel", "Kernel", "applications-engineering-symbolic")

        # --- 3: MAINTENANCE ---
        page_maint = Adw.PreferencesPage()
        
        sys_maint_group = Adw.PreferencesGroup(title="System Fixes")
        for title, sub, job in [("Fix Broken Packages", "Repairs installations.", "fix_broken"), ("Fix Update Errors", "Clears corrupted apt lists.", "fix_updates"), ("Restart Network Services", "Fixes dropped Wi-Fi.", "fix_network"), ("Fix NVIDIA Black Screens", "Forces X11 fallback.", "fix_wayland"), ("Clean Package Cache", "Frees disk space.", "clean_cache")]:
            sys_maint_group.add(self.create_maintenance_group_row(title, sub, job, True))
        page_maint.add(sys_maint_group)

        gnome_maint_group = Adw.PreferencesGroup(title="GNOME Resets")
        for title, sub, job in [("Reset Ubuntu Dock", "Restores factory default.", "fix_dock"), ("Disable Extensions", "Unfreezes broken desktop.", "fix_extensions"), ("Clear Thumbnail Cache", "Fixes corrupted images.", "fix_thumbnails")]:
            gnome_maint_group.add(self.create_maintenance_group_row(title, sub, job, False))
        page_maint.add(gnome_maint_group)

        kde_maint_group = Adw.PreferencesGroup(title="KDE Plasma Resets")
        for title, sub, job in [("Restart Plasma Shell", "Fixes frozen taskbar.", "kde_shell"), ("Fix Broken Plasmoids", "Clears QML cache.", "kde_plasmoids"), ("Restart KWin", "Fixes stuttering animations.", "kde_kwin"), ("Clear Icon Cache", "Fixes missing app icons.", "kde_icon_cache")]:
            kde_maint_group.add(self.create_maintenance_group_row(title, sub, job, False))
        page_maint.add(kde_maint_group)

        uni_maint_group = Adw.PreferencesGroup(title="Universal Resets")
        for title, sub, job in [("Reset Monitors and Resolutions", "Fixes resolution locks.", "fix_monitors"), ("Restart Audio Engine", "Restarts PipeWire.", "fix_audio")]:
            uni_maint_group.add(self.create_maintenance_group_row(title, sub, job, False))
        page_maint.add(uni_maint_group)

        self.view_stack.add_titled_with_icon(page_maint, "maintenance", "Maintenance", "preferences-system-symbolic")

        # --- MASSIVE SOFTWARE HUB GENERATOR ---
        categories = [
            ("Bundles", "Macro Bundles", "applications-science-symbolic", [
                ("OBS Studio Ultimate Stack", "Installs Flatpak and 8 plugins", "obs_ultimate", None, "com.obsproject.Studio"),
                ("Virtual Desktop Combo", "Docker, FreeRDP, Winboat", "virt_desktop_combo", "docker", None),
                ("Virt-Manager Setup", "KVM/QEMU setup", "virt_manager", "virt-manager", None),
                ("LAMP Stack Developer", "Apache, MySQL, PHP", "install_lamp", "apache2", None),
                ("Ultimate Emulation Pack", "RetroArch, PCSX2, RPCS3, Dolphin", "install_emulators", None, "org.libretro.RetroArch"),
                ("Game Dev Essentials", "Godot, Blender, Krita", "install_gamedev", None, "org.godotengine.Godot"),
                ("Streaming Setup", "OBS, Audacity, EasyEffects", "install_streaming", "easyeffects", None)
            ]),
            ("Browsers", "Web Browsers", "network-wired-symbolic", [
                ("Google Chrome", "Proprietary binary", "install_chrome", "google-chrome", None),
                ("Microsoft Edge", "Proprietary binary", "install_edge", "microsoft-edge", None),
                ("Brave", "Privacy focused", "install_brave", "brave-browser", None),
                ("Vivaldi", "Highly customizable", "vivaldi-stable", "vivaldi", None),
                ("Opera", "With built-in VPN", "opera-stable", "opera", None),
                ("Firefox", "Flatpak edition", "fp:org.mozilla.firefox", None, "org.mozilla.firefox"),
                ("Zen Browser", "Minimalist browser", "fp:io.github.zen_browser.zen", None, "io.github.zen_browser.zen"),
                ("Chromium", "Open source base", "fp:org.chromium.Chromium", None, "org.chromium.Chromium"),
                ("Ungoogled Chromium", "Chromium without Google", "fp:io.github.ungoogled_software.ungoogled_chromium", None, "io.github.ungoogled_software.ungoogled_chromium"),
                ("Waterfox", "Privacy browser", "fp:net.waterfox.waterfox", None, "net.waterfox.waterfox"),
                ("LibreWolf", "Hardened Firefox", "fp:io.gitlab.librewolf-community", None, "io.gitlab.librewolf-community"),
                ("Floorp", "Japanese Firefox fork", "fp:ablaze.floorp.Floorp", None, "ablaze.floorp.Floorp"),
                ("Mullvad Browser", "Anti-tracking", "fp:net.mullvad.MullvadBrowser", None, "net.mullvad.MullvadBrowser"),
                ("DuckDuckGo", "Privacy browser", "fp:com.duckduckgo.Desktop", None, "com.duckduckgo.Desktop"),
                ("Epiphany", "GNOME Web", "epiphany-browser", "epiphany-browser", None),
                ("Falkon", "KDE Browser", "falkon", "falkon", None),
                ("Pale Moon", "Independent engine", "fp:org.palemoon.PaleMoon", None, "org.palemoon.PaleMoon"),
                ("Tor Browser", "Dark-web access", "fp:com.github.micahflee.torbrowser-launcher", None, "com.github.micahflee.torbrowser-launcher"),
                ("Thorium", "AVX2 Optimized Chrome", "install_thorium", "thorium-browser", None)
            ]),
            ("Gaming", "Gaming and Emulation", "input-gaming-symbolic", [
                ("Steam", "Essential Client", "install_steam", "steam", None),
                ("Lutris", "Game Manager", "lutris", "lutris", None),
                ("Heroic", "Epic and GOG", "fp:com.heroicgameslauncher.hgl", None, "com.heroicgameslauncher.hgl"),
                ("Bottles", "Windows Environments", "fp:com.usebottles.bottles", None, "com.usebottles.bottles"),
                ("Cartridges", "Unified Library", "fp:hu.irl.Cartridges", None, "hu.irl.Cartridges"),
                ("ProtonPlus", "Proton Manager", "fp:com.vysp3r.ProtonPlus", None, "com.vysp3r.ProtonPlus"),
                ("ProtonUp-Qt", "Custom Proton", "fp:net.davidotek.pupgui2", None, "net.davidotek.pupgui2"),
                ("MangoHud", "Vulkan Overlay", "mangohud", "mangohud", None),
                ("GOverlay", "MangoHud UI", "goverlay", "goverlay", None),
                ("Gamemode", "Feral Optimization", "gamemode", "gamemoded", None),
                ("Gamescope", "Micro-compositor", "gamescope", "gamescope", None),
                ("Protontricks", "Winetricks for Proton", "protontricks", "protontricks", None),
                ("Wine", "Compatibility layer", "wine", "wine", None),
                ("Winetricks", "Wine utility", "winetricks", "winetricks", None),
                ("Prism Launcher", "Minecraft Hub", "fp:org.prismlauncher.PrismLauncher", None, "org.prismlauncher.PrismLauncher"),
                ("Minecraft", "Official Launcher", "fp:com.mojang.Minecraft", None, "com.mojang.Minecraft"),
                ("Minigalaxy", "Native GOG Client", "fp:io.github.wouterfassm.Minigalaxy", None, "io.github.wouterfassm.Minigalaxy"),
                ("Ludusavi", "Save Backup Tool", "fp:com.github.mtkennerly.ludusavi", None, "com.github.mtkennerly.ludusavi"),
                ("PCSX2", "PS2 Emulator", "fp:net.pcsx2.PCSX2", None, "net.pcsx2.PCSX2"),
                ("RPCS3", "PS3 Emulator", "fp:net.rpcs3.RPCS3", None, "net.rpcs3.RPCS3"),
                ("RetroArch", "Multi-system Emulator", "fp:org.libretro.RetroArch", None, "org.libretro.RetroArch"),
                ("RuneLite", "OSRS Client", "fp:net.runelite.RuneLite", None, "net.runelite.RuneLite"),
                ("Vesktop", "Gaming Discord", "fp:dev.vencord.Vesktop", None, "dev.vencord.Vesktop")
            ]),
            ("Creative", "Content Creation", "camera-video-symbolic", [
                ("Blender", "3D creation", "blender", "blender", None),
                ("Kdenlive", "Video editor", "fp:org.kde.kdenlive", "kdenlive", "org.kde.kdenlive"),
                ("OpenShot", "Simple video editor", "openshot", "openshot", None),
                ("GIMP", "Image editor", "fp:org.gimp.GIMP", "gimp", "org.gimp.GIMP"),
                ("Krita", "Digital painting", "fp:org.kde.krita", "krita", "org.kde.krita"),
                ("Darktable", "RAW photo editor", "darktable", "darktable", None),
                ("Inkscape", "Vector graphics", "inkscape", "inkscape", None),
                ("FreeCAD", "Open Source CAD", "fp:org.freecadweb.FreeCAD", None, "org.freecadweb.FreeCAD"),
                ("Sweet Home 3D", "Interior Design", "sweethome3d", "sweethome3d", None),
                ("Godot Engine", "Game development", "fp:org.godotengine.Godot", None, "org.godotengine.Godot"),
                ("Natron", "Node compositing", "fp:fr.natron.Natron", None, "fr.natron.Natron"),
                ("Synfig Studio", "2D Animation", "fp:org.synfig.SynfigStudio", None, "org.synfig.SynfigStudio"),
                ("Pinta", "Simple drawing", "fp:org.pinta_project.Pinta", None, "org.pinta_project.Pinta"),
                ("Upscayl", "AI Upscaler", "fp:org.upscayl.Upscayl", None, "org.upscayl.Upscayl"),
                ("Audacity", "Audio editor", "audacity", "audacity", None),
                ("Tenacity", "Audacity fork", "fp:org.tenacityaudio.Tenacity", None, "org.tenacityaudio.Tenacity"),
                ("Ardour", "Professional DAW", "ardour", "ardour", None),
                ("LMMS", "Music production", "lmms", "lmms", None),
                ("Rosegarden", "MIDI sequencer", "rosegarden", "rosegarden", None),
                ("Pavucontrol", "Audio mixer", "pavucontrol", "pavucontrol", None),
                ("EasyEffects", "Audio effects", "easyeffects", "easyeffects", None),
                ("Handbrake", "Video transcoder", "fp:fr.handbrake.ghb", "handbrake", "fr.handbrake.ghb"),
                ("Pitivi", "Video Editor", "pitivi", "pitivi", None),
                ("Scribus", "Desktop Publishing", "scribus", "scribus", None),
                ("Figma (Unofficial)", "Design Tool", "fp:io.github.Figma_Linux.figma_linux", None, "io.github.Figma_Linux.figma_linux")
            ]),
            ("Office", "Office and Comms", "mail-send-symbolic", [
                ("LibreOffice", "Office Suite", "libreoffice", "libreoffice", None),
                ("OnlyOffice", "Modern Office", "fp:org.onlyoffice.desktopeditors", None, "org.onlyoffice.desktopeditors"),
                ("WPS Office", "Office compatibility", "fp:com.wps.Office", None, "com.wps.Office"),
                ("Obsidian", "Markdown Notes", "fp:md.obsidian.Obsidian", None, "md.obsidian.Obsidian"),
                ("Joplin", "Syncable Notes", "joplin", "joplin", None),
                ("Discord", "Voice Chat", "fp:com.discordapp.Discord", None, "com.discordapp.Discord"),
                ("Thunderbird", "Email Client", "fp:org.mozilla.Thunderbird", "thunderbird", "org.mozilla.Thunderbird"),
                ("BlueMail", "Email Client", "fp:me.bluemail.BlueMail", None, "me.bluemail.BlueMail"),
                ("Mailspring", "Email Client", "fp:com.getmailspring.Mailspring", None, "com.getmailspring.Mailspring"),
                ("Teams for Linux", "Microsoft Teams", "fp:com.github.IsmaelMartinez.teams_for_linux", None, "com.github.IsmaelMartinez.teams_for_linux"),
                ("Zoom", "Video Conferencing", "fp:us.zoom.Zoom", None, "us.zoom.Zoom"),
                ("Telegram", "Secure Messaging", "fp:org.telegram.desktop", None, "org.telegram.desktop"),
                ("Signal", "Secure Messaging", "fp:org.signal.Signal", None, "org.signal.Signal"),
                ("Slack", "Team Comms", "fp:com.slack.Slack", None, "com.slack.Slack"),
                ("Element", "Matrix Client", "fp:im.riot.Riot", None, "im.riot.Riot"),
                ("Evince", "GNOME PDF", "evince", "evince", None),
                ("Papers", "Modern PDF", "papers", "papers", None),
                ("Okular", "KDE PDF", "okular", "okular", None),
                ("Foliate", "E-Book Reader", "fp:com.github.johnfactotum.Foliate", None, "com.github.johnfactotum.Foliate"),
                ("PDFArranger", "PDF utility", "pdfarranger", "pdfarranger", None),
                ("Simple-scan", "GNOME Scan", "simple-scan", "simple-scan", None),
                ("Skanlite", "KDE Scan", "skanlite", "skanlite", None),
                ("GNOME Contacts", "Contacts", "gnome-contacts", "gnome-contacts", None),
                ("GNOME Calendar", "Calendar", "gnome-calendar", "gnome-calendar", None),
                ("KDE Connect", "Phone sync", "kdeconnect", "kdeconnect-cli", None)
            ]),
            ("Media", "Media and Streaming", "multimedia-player-symbolic", [
                ("VLC", "Universal player", "vlc", "vlc", None),
                ("MPV", "Minimalist player", "mpv", "mpv", None),
                ("Celluloid", "GTK Media Player", "celluloid", "celluloid", None),
                ("SMPlayer", "Advanced MPlayer GUI", "smplayer", "smplayer", None),
                ("Haruna", "KDE Video Player", "haruna", "haruna", None),
                ("Showtime", "GNOME Video Player", "showtime", "showtime", None),
                ("FreeTube", "Private YouTube client", "fp:io.freetubeapp.FreeTube", None, "io.freetubeapp.FreeTube"),
                ("Spotify", "Music Streaming", "fp:com.spotify.Client", None, "com.spotify.Client"),
                ("Audacious", "Lightweight Audio Player", "audacious", "audacious", None),
                ("Amberol", "Simple Music Player", "fp:io.bassi.Amberol", None, "io.bassi.Amberol"),
                ("Cider", "Apple Music Client", "fp:sh.cider.Cider", None, "sh.cider.Cider"),
                ("Strawberry", "Audiophile player", "strawberry", "strawberry", None),
                ("Clementine", "Music player", "clementine", "clementine", None),
                ("Lollypop", "GNOME Music", "lollypop", "lollypop", None),
                ("Rhythmbox", "Classic Music", "rhythmbox", "rhythmbox", None),
                ("Elisa", "KDE Music", "elisa", "elisa", None),
                ("GNOME Music", "GNOME Audio", "gnome-music", "gnome-music", None),
                ("Shortwave", "Internet Radio", "fp:de.haeckerfelix.Shortwave", None, "de.haeckerfelix.Shortwave"),
                ("Pocket Casts", "Podcasts", "fp:com.github.fabiocollet.pocketcasts", None, "com.github.fabiocollet.pocketcasts"),
                ("Kamoso", "Camera tool", "kamoso", "kamoso", None),
                ("Plex", "Media Player", "fp:tv.plex.PlexDesktop", None, "tv.plex.PlexDesktop"),
                ("Jellyfin", "Media Player", "fp:com.github.iwalton3.jellyfin-media-player", None, "com.github.iwalton3.jellyfin-media-player"),
                ("Stremio", "Video Streaming", "fp:com.stremio.Stremio", None, "com.stremio.Stremio"),
                ("Kodi", "Media Center", "fp:tv.kodi.Kodi", None, "tv.kodi.Kodi"),
                ("Hypnotix", "IPTV Player", "hypnotix", "hypnotix", None),
                ("StreamController", "Elgato alternative", "fp:com.core447.StreamController", None, "com.core447.StreamController")
            ]),
            ("Tools", "System Tools", "emblem-system-symbolic", [
                ("Mission Center", "Windows-style Task Manager", "fp:io.missioncenter.MissionCenter", None, "io.missioncenter.MissionCenter"),
                ("Extension Manager", "GNOME Extensions", "extension-manager", "extension-manager", None),
                ("GNOME Tweaks", "GNOME Customization", "gnome-tweaks", "gnome-tweaks", None),
                ("Stacer", "System Optimizer", "stacer", "stacer", None),
                ("LACT", "Linux AMDGUI Controller", "install_lact", "lact", None),
                ("Htop", "Interactive Process Viewer", "htop", "htop", None),
                ("Psensor", "Temperature Monitor", "psensor", "psensor", None),
                ("Flatseal", "Flatpak Permissions", "fp:com.github.tchx84.Flatseal", None, "com.github.tchx84.Flatseal"),
                ("Warehouse", "Flatpak Manager", "fp:io.github.flattool.Warehouse", None, "io.github.flattool.Warehouse"),
                ("Hidamari", "Video Wallpapers", "fp:io.github.jeffshee.Hidamari", None, "io.github.jeffshee.Hidamari"),
                ("GtkStressTesting", "Hardware Stress", "fp:com.leinardi.gst", None, "com.leinardi.gst"),
                ("Bitwarden", "Password Manager", "fp:com.bitwarden.desktop", None, "com.bitwarden.desktop"),
                ("KeePassXC", "Offline Passwords", "keepassxc", "keepassxc", None),
                ("RustDesk", "Remote Desktop", "fp:com.rustdesk.RustDesk", None, "com.rustdesk.RustDesk"),
                ("TeamViewer", "Remote Support", "teamviewer", "teamviewer", None),
                ("AnyDesk", "Remote Support", "anydesk", "anydesk", None),
                ("Remmina", "RDP Client", "remmina", "remmina", None),
                ("Timeshift", "System Backup", "timeshift", "timeshift", None),
                ("GParted", "Partition Manager", "gparted", "gparted", None),
                ("KDE Partition Manager", "KDE Partitions", "partitionmanager", "partitionmanager", None),
                ("Syncthing", "File Sync", "syncthing", "syncthing", None),
                ("BleachBit", "System Cleaner", "bleachbit", "bleachbit", None),
                ("CPU-X", "CPU-Z Alternative", "cpu-x", "cpu-x", None),
                ("Git", "Version Control", "git", "git", None),
                ("7zip", "Archive Manager", "7zip", "7zz", None),
                ("fastfetch", "System Info CLI", "fastfetch", "fastfetch", None),
                ("Kvantum", "Qt Styling", "qt6-style-kvantum", "kvantummanager", None)
            ])
        ]

        for tab_id, tab_title, icon, apps in categories:
            page = Adw.PreferencesPage()
            
            if tab_id == "Bundles":
                res_grp = Adw.PreferencesGroup(title="DaVinci Resolve Setup", description="3-Step automated setup and fix process.")
                
                # Step 1: Link
                row1 = Adw.ActionRow(title="Step 1: Download Resolve", subtitle="Choose Free or Studio from Blackmagic.")
                link_btn = Gtk.LinkButton(uri="https://www.blackmagicdesign.com/products/davinciresolve", label="Open Website")
                link_btn.set_valign(Gtk.Align.CENTER)
                row1.add_suffix(link_btn)
                res_grp.add(row1)

                # Step 2: Select File
                row2 = Adw.ActionRow(title="Step 2: Select Downloaded .zip", subtitle="Point to the file you downloaded.")
                self.resolve_path_lbl = Gtk.Label(label="No file selected")
                self.resolve_path_lbl.set_valign(Gtk.Align.CENTER)
                self.resolve_path_lbl.set_margin_end(10)
                browse_btn = Gtk.Button(label="Browse...", valign=Gtk.Align.CENTER, css_classes=["pill"])
                browse_btn.connect("clicked", self.on_resolve_browse)
                box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
                box2.append(self.resolve_path_lbl)
                box2.append(browse_btn)
                row2.add_suffix(box2)
                res_grp.add(row2)

                # Step 3: Execute
                row3 = Adw.ActionRow(title="Step 3: Execute", subtitle="Extracts, installs, grabs ROCm, and patches libraries.")
                box3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                install_btn = Gtk.Button(label="Install Resolve", valign=Gtk.Align.CENTER, css_classes=["suggested-action", "pill"])
                install_btn.connect("clicked", self.on_resolve_install)
                update_btn = Gtk.Button(label="Update Resolve", valign=Gtk.Align.CENTER, css_classes=["pill"])
                update_btn.connect("clicked", self.on_resolve_update)
                box3.append(install_btn)
                box3.append(update_btn)
                row3.add_suffix(box3)
                res_grp.add(row3)
                
                page.add(res_grp)

            grp = Adw.PreferencesGroup(title=tab_title)
            for title, sub, job, apt, fp in apps:
                row = Adw.ActionRow(title=title, subtitle=sub)
                installed = is_app_installed(apt, fp)
                btn = Gtk.Button(label="Installed" if installed else "Install", valign=Gtk.Align.CENTER)
                btn.set_sensitive(not installed)
                if not installed:
                    btn.add_css_class("suggested-action")
                    btn.add_css_class("pill")
                    btn.connect("clicked", lambda b, j=job, a=apt, f=fp: self.run_sw(b, j, a, f))
                row.add_suffix(btn)
                grp.add(row)
            page.add(grp)
            self.view_stack.add_titled_with_icon(page, tab_id.lower(), tab_id, icon)

        # --- HEADER BAR & MENU ---
        switcher = Adw.ViewSwitcher(stack=self.view_stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        header = Adw.HeaderBar(title_widget=switcher)
        
        # The Restored Gear Icon
        menu_btn = Gtk.MenuButton(icon_name="preferences-system-symbolic")
        popover = Gtk.Popover()
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)

        theme_lbl = Gtk.Label(label="Theme", halign=Gtk.Align.START, css_classes=["dim-label"])
        pop_box.append(theme_lbl)
        
        theme_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        for label, val in [("Auto", 0), ("Light", 1), ("Dark", 2)]:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", self.set_theme, val)
            self.theme_btns.append(btn)
            theme_box.append(btn)
        
        # Highlight current theme
        self.theme_btns[0].add_css_class("suggested-action")
        pop_box.append(theme_box)

        pop_box.append(Gtk.Separator(margin_top=5, margin_bottom=5))

        about_btn = Gtk.Button(label="About Welcome to Darkside")
        about_btn.connect("clicked", self.show_about_window)
        pop_box.append(about_btn)

        popover.set_child(pop_box)
        menu_btn.set_popover(popover)
        header.pack_end(menu_btn)
        
        box.append(header)
        box.append(self.view_stack)
        self.main_stack.add_named(box, "dashboard_screen")

    # --- ACTION HANDLERS ---
    def on_resolve_browse(self, btn):
        dialog = Gtk.FileDialog(title="Select DaVinci Resolve .zip")
        dialog.open(self, None, self._on_zip_selected)

    def _on_zip_selected(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            self.resolve_zip_path = file.get_path()
            self.resolve_path_lbl.set_label(os.path.basename(self.resolve_zip_path))
        except Exception: pass

    def on_resolve_install(self, btn):
        if not hasattr(self, 'resolve_zip_path') or not self.resolve_zip_path:
            btn.set_label("Select file first!")
            GLib.timeout_add(2000, lambda: btn.set_label("Install Resolve"))
            return
        btn.set_label("Extracting...")
        btn.set_sensitive(False)
        threading.Thread(target=self._exec_resolve, args=(btn, self.resolve_zip_path, "resolve_install")).start()

    def on_resolve_update(self, btn):
        if not hasattr(self, 'resolve_zip_path') or not self.resolve_zip_path:
            btn.set_label("Select file first!")
            GLib.timeout_add(2000, lambda: btn.set_label("Update Resolve"))
            return
        btn.set_label("Updating...")
        btn.set_sensitive(False)
        threading.Thread(target=self._exec_resolve, args=(btn, self.resolve_zip_path, "resolve_update")).start()

    def _exec_resolve(self, btn, path, job_name):
        try:
            subprocess.run(["pkexec", "bash", "/usr/share/welcome-to-darkside/software_engine.sh", job_name, path], check=True)
            GLib.idle_add(lambda: btn.set_label("Success!"))
        except:
            GLib.idle_add(lambda: btn.set_label("Failed"))
        finally:
            GLib.idle_add(lambda: btn.set_sensitive(True))

    def create_maintenance_group_row(self, title, subtitle, job_name, root):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        btn = Gtk.Button(label="Run Fix", valign=Gtk.Align.CENTER, css_classes=["pill"])
        btn.connect("clicked", self.run_maintenance_job, job_name, root)
        row.add_suffix(btn)
        return row

    def set_theme(self, button, theme_mode):
        style_manager = Adw.StyleManager.get_default()
        modes = [Adw.ColorScheme.DEFAULT, Adw.ColorScheme.FORCE_LIGHT, Adw.ColorScheme.FORCE_DARK]
        style_manager.set_color_scheme(modes[theme_mode])
        for btn in self.theme_btns:
            btn.remove_css_class("suggested-action")
        button.add_css_class("suggested-action")

    def show_about_window(self, button):
        about = Adw.AboutWindow(transient_for=self, application_name="Welcome to Darkside", developer_name="Steve Darkside QC", version="1.0.0 (26.04 Core)")
        about.set_application_icon("welcome-to-darkside")
        about.add_link("GitHub", "https://github.com/SteveDarksideQC")
        about.add_link("YouTube", "https://www.youtube.com/@SteveDarksideQC")
        about.add_link("Ko-fi", "https://ko-fi.com/stevedarksideqc")
        about.add_link("PayPal", "https://paypal.me/SteveDarksideQC")
        about.present()

    def on_master_toggled(self, switch, gparam):
        if self.is_initializing_ui: return
        state = "on" if switch.get_active() else "off"
        self.is_initializing_ui = True
        for child in self.child_switches: child.set_active(switch.get_active())
        self.is_initializing_ui = False
        sh_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "toggle_master.sh")
        try: subprocess.run(["pkexec", "bash", sh_path, state], check=True)
        except subprocess.CalledProcessError: pass

    def on_tweak_toggled(self, switch, gparam, tweak_name):
        if self.is_initializing_ui: return
        state = "on" if switch.get_active() else "off"
        sh_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "toggle_tweak.sh")
        try: subprocess.run(["pkexec", "bash", sh_path, tweak_name, state], check=True)
        except subprocess.CalledProcessError:
            self.is_initializing_ui = True
            switch.set_active(not switch.get_active())
            self.is_initializing_ui = False

    def run_maintenance_job(self, button, job_name, requires_root):
        button.set_label("Running...")
        button.set_sensitive(False)
        threading.Thread(target=self._exec_maintenance, args=(button, job_name, requires_root)).start()

    def _exec_maintenance(self, button, job_name, requires_root):
        try:
            if requires_root:
                sh_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "maintenance.sh")
                subprocess.run(["pkexec", "bash", sh_path, job_name], check=True)
            else:
                if job_name == "fix_extensions": subprocess.run(["gsettings", "set", "org.gnome.shell", "disable-user-extensions", "true"], check=True)
                elif job_name == "fix_dock": subprocess.run(["dconf", "reset", "-f", "/org/gnome/shell/extensions/dash-to-dock/"], check=True)
                elif job_name == "fix_thumbnails": os.system("rm -rf ~/.cache/thumbnails/*")
                elif job_name == "kde_shell": subprocess.run(["systemctl", "--user", "restart", "plasma-plasmashell.service"], check=True)
                elif job_name == "kde_kwin": subprocess.run(["systemctl", "--user", "restart", "plasma-kwin_wayland.service"], check=True)
                elif job_name == "kde_plasmoids": 
                    os.system("rm -rf ~/.cache/org.kde.plasmashell*")
                    subprocess.run(["kbuildsycoca6", "--noincremental"], check=True)
                elif job_name == "kde_icon_cache": os.system("rm -rf ~/.cache/icon-cache.kcache")
                elif job_name == "fix_monitors":
                    monitors_path = os.path.expanduser("~/.config/monitors.xml")
                    if os.path.exists(monitors_path): os.remove(monitors_path)
                    kscreen_path = os.path.expanduser("~/.local/share/kscreen")
                    if os.path.exists(kscreen_path): os.system(f"rm -rf {kscreen_path}/*")
                elif job_name == "fix_audio":
                    subprocess.run(["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"], check=True)
            GLib.idle_add(lambda: button.set_label("Done"))
        except Exception:
            GLib.idle_add(lambda: button.set_label("Failed"))
        finally:
            GLib.idle_add(lambda: button.set_sensitive(True))
            GLib.timeout_add(3000, lambda: button.set_label("Run Fix") if "update_grub" not in job_name else "Run")

    def run_kernel_job(self, button, job_name):
        button.set_label("Installing...")
        button.set_sensitive(False)
        threading.Thread(target=self._exec_kernel_job, args=(button, job_name)).start()

    def _exec_kernel_job(self, button, job_name):
        try:
            sh_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "kernel_engine.sh")
            subprocess.run(["pkexec", "bash", sh_path, job_name], check=True)
            GLib.idle_add(lambda: button.set_label("Installed! Reboot Req."))
        except subprocess.CalledProcessError:
            GLib.idle_add(lambda: button.set_label("Failed / Canceled"))
        finally:
            GLib.idle_add(lambda: button.set_sensitive(True))
            GLib.timeout_add(5000, lambda: button.set_label("Install") if job_name != "build_tkg" else "Build Kernel")

    def run_sw(self, button, job_name, apt_cmd, flatpak_id):
        button.set_label("Running...")
        button.set_sensitive(False)
        threading.Thread(target=self._exec_software_job, args=(button, job_name, apt_cmd, flatpak_id)).start()

    def _exec_software_job(self, button, job_name, apt_cmd, flatpak_id):
        try:
            sh_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "software_engine.sh")
            subprocess.run(["pkexec", "bash", sh_path, job_name], check=True)
            
            if is_app_installed(apt_cmd=apt_cmd, flatpak_id=flatpak_id):
                GLib.idle_add(lambda: button.set_label("Installed"))
                GLib.idle_add(lambda: button.remove_css_class("suggested-action"))
            else:
                GLib.idle_add(lambda: button.set_label("Failed"))
                GLib.idle_add(lambda: button.set_sensitive(True))
        except subprocess.CalledProcessError:
            GLib.idle_add(lambda: button.set_label("Failed / Canceled"))
            GLib.idle_add(lambda: button.set_sensitive(True))

    def pulse_progress(self):
        if self.is_task_running: self.progress_bar.pulse(); return True
        return False

    def on_setup_safety_clicked(self, button):
        self.setup_btn.set_visible(False)
        self.skip_btn.set_visible(False)
        self.progress_bar.set_visible(True)
        self.is_task_running = True
        GLib.timeout_add(50, self.pulse_progress)
        threading.Thread(target=self.run_timeshift_backend).start()

    def run_timeshift_backend(self):
        sh_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "setup_timeshift.sh")
        try:
            subprocess.run(["pkexec", "bash", sh_path], check=True, capture_output=True, text=True)
            with open(SAFETY_FLAG_FILE, 'w') as f: f.write("done")
            self.is_task_running = False
            GLib.idle_add(self.show_next_button)
        except subprocess.CalledProcessError:
            self.is_task_running = False
            GLib.idle_add(self.reset_safety_buttons)

    def show_next_button(self):
        self.progress_bar.set_visible(False)
        self.next_btn.set_visible(True)

    def reset_safety_buttons(self):
        self.progress_bar.set_visible(False)
        self.setup_btn.set_visible(True)
        self.skip_btn.set_visible(True)
        self.setup_btn.set_label("Setup Failed - Try Again")

    def on_skip_safety_clicked(self, button):
        with open(SAFETY_FLAG_FILE, 'w') as f: f.write("skipped")
        self.main_stack.set_visible_child_name("dashboard_screen")
        
    def on_next_clicked(self, button):
        self.main_stack.set_visible_child_name("dashboard_screen")

class DarksideApp(Adw.Application):
    def __init__(self): super().__init__(application_id='com.stevedarksideqc.WelcomeToDarkside', flags=Gio.ApplicationFlags.FLAGS_NONE)
    def do_activate(self):
        win = self.props.active_window
        if not win: win = DarksideWindow(application=self)
        win.present()

if __name__ == '__main__':
    app = DarksideApp()
    sys.exit(app.run(sys.argv))
