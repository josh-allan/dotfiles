-- Set to true if you have a Nerd Font installed
vim.g.have_nerd_font = true

-- Bootstrap lazy.nvim to source plugins

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
	local lazyrepo = "https://github.com/folke/lazy.nvim.git"
	vim.fn.system({ "git", "clone", "--filter=blob:none", "--branch=stable", lazyrepo, lazypath })
end ---@diagnostic disable-next-line: undefined-field
vim.opt.rtp:prepend(lazypath)
require("lazy").setup("plugins")
require("base")
-- custom autocmds
-- Treesitter automatic Python format strings
