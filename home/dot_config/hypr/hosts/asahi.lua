-- asahi host-specific Hyprland overrides. Ported from host.conf.
hl.env("AQ_DRM_DEVICES", "/dev/dri/renderD128:/dev/dri/card2")

hl.workspace_rule({ workspace = "1", monitor = "eDP-1", default = true })
