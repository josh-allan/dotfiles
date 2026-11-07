for _, binding in ipairs(require("keybinds")) do
	rex.bind(binding[1], binding[2], binding[3])
end
