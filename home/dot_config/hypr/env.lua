hl.env("XCURSOR_SIZE", "24")
hl.env("WLR_NO_HARDWARE_CURSORS", "1")
hl.env("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
hl.env("GNOME_KEYRING_CONTROL", "/run/user/1000/keyring")

-- GE-Proton (11-12+) defaults for every Steam game; opt out per game with VAR=0.
-- Native Wine Wayland, and report HDR so cm_auto_hdr can switch the SDR desktop
-- to HDR for fullscreen games (every display on these hosts is HDR).
hl.env("PROTON_ENABLE_WAYLAND", "1")
hl.env("PROTON_FORCE_HDR", "1")
