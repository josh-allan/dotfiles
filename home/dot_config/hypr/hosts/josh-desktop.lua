-- josh-desktop host overrides.

-- RX 9070 (RDNA4): upgrade FSR 3.1 games to FSR 4. Opt out per game with PROTON_FSR4_UPGRADE=0.
hl.env("PROTON_FSR4_UPGRADE", "1")

-- Headless cage (steam-bpm.service) starts at boot and claims wayland-0.
-- Hyprland's Wayland backend then connects to it and adds a 0x0 WAYLAND-1
-- output, which would take the next free workspace (3). Park it on 9 instead.
hl.workspace_rule({ workspace = "9", monitor = "WAYLAND-1", default = true })
-- Pin the rest to DP-3, or WAYLAND-1 takes the lowest free number when workspaces move
-- (config reload, monitor change) and SUPER+N then focuses an invisible output.
for i = 1, 8 do
	hl.workspace_rule({ workspace = tostring(i), monitor = "DP-3" })
end

-- OLED: keep the Wayle bar hidden except on top-edge hover and workspace switches.
hl.on("hyprland.start", function()
	hl.exec_cmd("/home/josh/.local/bin/wayle-autohide")
end)
