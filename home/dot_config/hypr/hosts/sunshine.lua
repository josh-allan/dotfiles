-- josh-desktop host overrides.

-- Headless cage (steam-bpm.service) starts at boot and claims wayland-0.
-- Hyprland's Wayland backend then connects to it and adds a 0x0 WAYLAND-1
-- output, which would take the next free workspace (3). Park it on 9 instead.
hl.workspace_rule({ workspace = "9", monitor = "WAYLAND-1", default = true })
-- Pin the rest to DP-3, or WAYLAND-1 takes the lowest free number when workspaces move
-- (config reload, monitor change) and SUPER+N then focuses an invisible output.
for i = 1, 8 do
	hl.workspace_rule({ workspace = tostring(i), monitor = "DP-3" })
end
