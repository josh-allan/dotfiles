for _, binding in ipairs(require("keybinds")) do
	if type(binding[2]) == "function" then
		rex.bind(binding[1], binding[2])
	else
		rex.bind(binding[1], binding[2], binding[3])
	end
end
require("floats").setup()
require("attention").setup()
