local map = vim.api.nvim_set_keymap
local opts = { noremap = true, silent = true }
local keymap = vim.keymap

-- Set <space> as the leader key
-- See `:help mapleader`
vim.g.mapleader = " "
vim.g.maplocalleader = " "

keymap.set("n", "<leader>sv", "<C-w>v") -- split window vertically
keymap.set("n", "<leader>sh", "<C-w>s") -- split window horizontally
keymap.set("n", "<leader>se", "<C-w>=") -- make split windows equal width & height
keymap.set("n", "<leader>sx", ":close<CR>") -- close current split window

keymap.set("n", "<leader>to", ":tabnew<CR>") -- open new tab
keymap.set("n", "<leader>tx", ":tabclose<CR>") -- close current tab
keymap.set("n", "<leader>tn", ":tabn<CR>") --  go to next tab
keymap.set("n", "<leader>tp", ":tabp<CR>") --  go to previous tab
keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>")
-- Diagnostic keymaps
keymap.set("n", "[d", vim.diagnostic.goto_prev, { desc = "Go to previous [D]iagnostic message" })
keymap.set("n", "]d", vim.diagnostic.goto_next, { desc = "Go to next [D]iagnostic message" })
keymap.set("n", "<leader>e", vim.diagnostic.open_float, { desc = "Show diagnostic [E]rror messages" })
keymap.set("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Open diagnostic [Q]uickfix list" })

-- Exit terminal mode in the builtin terminal with a shortcut that is a bit easier
-- for people to discover. Otherwise, you normally need to press <C-\><C-n>, which
-- is not what someone will guess without a bit more experience.
--
-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })

-- TIP: Disable arrow keys in normal mode
keymap.set("n", "<left>", '<cmd>echo "Use h to move!!"<CR>')
keymap.set("n", "<right>", '<cmd>echo "Use l to move!!"<CR>')
keymap.set("n", "<up>", '<cmd>echo "Use k to move!!"<CR>')
keymap.set("n", "<down>", '<cmd>echo "Use j to move!!"<CR>')

-- Keybinds to make split navigation easier.
-- Use CTRL+<hjkl> to switch between windows
--
--  See `:help wincmd` for avlist of all window commands
keymap.set("n", "<C-h>", "<C-w><C-h>", { desc = "Move focus to the left window" })
keymap.set("n", "<C-l>", "<C-w><C-l>", { desc = "Move focus to the right window" })
keymap.set("n", "<C-j>", "<C-w><C-j>", { desc = "Move focus to the lower window" })
keymap.set("n", "<C-k>", "<C-w><C-k>", { desc = "Move focus to the upper window" })

keymap.set("n", "<C-,>", "<cmd>BufferPrevious<CR>")

-- Move to previous/next

map("n", "<C->>", "<Cmd>BufferMoveNext<CR>", opts)
-- Goto buffer in position...
map("n", "<C-1>", "<Cmd>BufferGoto 1<CR>", opts)
map("n", "<C-2>", "<Cmd>BufferGoto 2<CR>", opts)
map("n", "<C-3>", "<Cmd>BufferGoto 3<CR>", opts)
map("n", "<C-4>", "<Cmd>BufferGoto 4<CR>", opts)
map("n", "<C-5>", "<Cmd>BufferGoto 5<CR>", opts)
map("n", "<C-6>", "<Cmd>BufferGoto 6<CR>", opts)
map("n", "<C-7>", "<Cmd>BufferGoto 7<CR>", opts)
map("n", "<C-8>", "<Cmd>BufferGoto 8<CR>", opts)
map("n", "<C-9>", "<Cmd>BufferGoto 9<CR>", opts)
map("n", "<C-0>", "<Cmd>BufferLast<CR>", opts)
-- Pin/unpin buffer
map("n", "<C-p>", "<Cmd>BufferPin<CR>", opts)
-- Close buffer
map("n", "<C-c>", "<Cmd>BufferClose<CR>", opts)
-- Wipeout buffer
--                 :BufferWipeout
-- Close commands
--                 :BufferCloseAllButCurrent
--                 :BufferCloseAllButPinned
--                 :BufferCloseAllButCurrentOrPinned
--                 :BufferCloseBuffersLeft
--                 :BufferCloseBuffersRight
-- Magic buffer-picking mode
map("n", "<C-p>", "<Cmd>BufferPick<CR>", opts)
-- Sort automatically by...
map("n", "<Space>bb", "<Cmd>BufferOrderByBufferNumber<CR>", opts)
map("n", "<Space>bn", "<Cmd>BufferOrderByName<CR>", opts)
map("n", "<Space>bd", "<Cmd>BufferOrderByDirectory<CR>", opts)
map("n", "<Space>bl", "<Cmd>BufferOrderByLanguage<CR>", opts)
map("n", "<Space>bw", "<Cmd>BufferOrderByWindowNumber<CR>", opts)

-- Remove pesky trailing whitespaces
keymap.set("n", "<Leader>wt", [[:%s/\s\+$//e<cr>]])

-- Custom autocmds

-- Yank with highlight
vim.api.nvim_create_autocmd("TextYankPost", {
	desc = "Highlight when yanking (copying) text",
	group = vim.api.nvim_create_augroup("kickstart-highlight-yank", { clear = true }),
	callback = function()
		vim.highlight.on_yank()
	end,
})

vim.api.nvim_create_augroup("py-fstring", { clear = true })
vim.api.nvim_create_autocmd("InsertCharPre", {
	pattern = { "*.py" },
	group = "py-fstring",
	--- @param opts AutoCmdCallbackOpts
	--- @return nil
	callback = function(opts)
		-- Only run if f-string escape character is typed
		if vim.v.char ~= "{" then
			return
		end

		-- Get node and return early if not in a string
		local node = vim.treesitter.get_node()

		if not node then
			return
		end
		if node:type() ~= "string" then
			node = node:parent()
		end
		if not node or node:type() ~= "string" then
			return
		end

		vim.print(node:type())
		local row, col, _, _ = vim.treesitter.get_node_range(node)

		-- Return early if string is already a format string
		local first_char = vim.api.nvim_buf_get_text(opts.buf, row, col, row, col + 1, {})[1]
		vim.print("row " .. row .. " col " .. col)
		vim.print("char: '" .. first_char .. "'")
		if first_char == "f" then
			return
		end

		-- Otherwise, make the string a format string
		vim.api.nvim_input("<Esc>m'" .. row + 1 .. "gg" .. col + 1 .. "|if<Esc>`'la")
	end,
})
