-- vrr = 2: fullscreen only (desktop VRR flickers on OLED).
hl.monitor({ output = "DP-3", mode = "3440x1440@359.98", position = "0x0", scale = 1.0, bitdepth = 10, vrr = 2 })

-- 0x0 output from the headless cage session (see host.lua); keep it past DP-3's right edge.
hl.monitor({ output = "WAYLAND-1", mode = "0x0@60.0", position = "3440x0", scale = 1.0 })
