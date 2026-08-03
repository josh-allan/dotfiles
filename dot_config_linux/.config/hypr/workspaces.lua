-- Workspace-to-monitor bindings.
--
-- Hyprland otherwise assigns workspaces in monitor *detection* order, which is
-- not physical order, so 1 and 2 land on the wrong screens. Pin them to output
-- names instead. Physical layout comes from monitors.lua:
--   HDMI-A-1 at 0x0     -> left
--   DP-3     at 2560x0  -> right
--
-- Outputs absent on a given host are simply ignored by Hyprland, so this is
-- safe to share; per-host layouts belong in host.lua.

hl.workspace_rule({ workspace = "1", monitor = "HDMI-A-1", default = true })
hl.workspace_rule({ workspace = "2", monitor = "DP-3", default = true })
