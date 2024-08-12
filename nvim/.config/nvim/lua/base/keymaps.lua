local map = vim.api.nvim_set_keymap
local opts = { noremap = true, silent = true }
local keymap = vim.keymap

local helpers = require("base.helpers")

local nmap = helpers.nmap
local vmap = helpers.vmap
local xmap = helpers.xmap
local omap = helpers.omap
local noremap = helpers.noremap
local nnoremap = helpers.nnoremap
local inoremap = helpers.inoremap
local vnoremap = helpers.vnoremap
local xnoremap = helpers.xnoremap
local onoremap = helpers.onoremap
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

keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })

-- Disable arrow keys in normal mode
keymap.set("n", "<left>", '<cmd>echo "Use h to move!!"<CR>')
keymap.set("n", "<right>", '<cmd>echo "Use l to move!!"<CR>')
keymap.set("n", "<up>", '<cmd>echo "Use k to move!!"<CR>')
keymap.set("n", "<down>", '<cmd>echo "Use j to move!!"<CR>')

-- Keybinds to make split navigation easier.
--
keymap.set("n", "<S-h>", "<C-w><C-h>", { desc = "Move focus to the left window" })
keymap.set("n", "<S-l>", "<C-w><C-l>", { desc = "Move focus to the right window" })
keymap.set("n", "<S-j>", "<C-w><C-j>", { desc = "Move focus to the lower window" })
keymap.set("n", "<S-k>", "<C-w><C-k>", { desc = "Move focus to the upper window" })
--
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

-- make 'Y' yank from current character to end of line
noremap("Y", "y$")
vnoremap("y", "ygv<ESC>")

-- Better indenting

nmap("<", "V<gv")
nmap(">", "V>gv")
xnoremap("<", "<gv")
xnoremap(">", ">gv")

-- Remove pesky trailing whitespaces
keymap.set("n", "<Leader>wt", [[:%s/\s\+$//e<cr>]])

-- Nvim Tree stuff
keymap.set("n", "<leader>e", "<cmd> Neotree toggle<CR>")
keymap.set("n", "<C-n", "<cmd> NvimTreeFocus <CR>")
--
-- Telescope
local builtin = require("telescope.builtin")
vim.keymap.set("n", "<leader>sh", builtin.help_tags, { desc = "[S]earch [H]elp" })
vim.keymap.set("n", "<leader>sk", builtin.keymaps, { desc = "[S]earch [K]eymaps" })
vim.keymap.set("n", "<leader>ff", builtin.find_files, { desc = "[S]earch [F]iles" })
vim.keymap.set("n", "<leader>sf", builtin.builtin, { desc = "[S]earch [S]elect Telescope" })
vim.keymap.set("n", "<leader>sw", builtin.grep_string, { desc = "[S]earch current [W]ord" })
vim.keymap.set("n", "<leader>sg", builtin.live_grep, { desc = "[S]earch by [G]rep" })
vim.keymap.set("n", "<leader>sd", builtin.diagnostics, { desc = "[S]earch [D]iagnostics" })
vim.keymap.set("n", "<leader>sr", builtin.resume, { desc = "[S]earch [R]esume" })
vim.keymap.set("n", "<leader>s.", builtin.oldfiles, { desc = '[S]earch Recent Files ("." for repeat)' })
vim.keymap.set("n", "<leader><leader>", builtin.buffers, { desc = "[ ] Find existing buffers" })

-- Debugger keybinds
local dap = require("dap")
local dapui = require("dapui")
vim.keymap.set("n", "<leader>dc", dap.continue, { desc = "Debug: Start/Continue" })
vim.keymap.set("n", "<leader>di", dap.step_into, { desc = "Debug: Step Into" })
vim.keymap.set("n", "<leader>do", dap.step_over, { desc = "Debug: Step Over" })
vim.keymap.set("n", "<leader>db", dap.step_out, { desc = "Debug: Step Out" })
vim.keymap.set("n", "<leader>b", dap.toggle_breakpoint, { desc = "Debug: Toggle Breakpoint" })
vim.keymap.set("n", "<leader>B", function()
	dap.set_breakpoint(vim.fn.input("Breakpoint condition: "))
end, { desc = "Debug: Set Breakpoint" })

-- Nvim git

keymap.set("n", "<leader>gb", function()
	MiniExtra.pickers.git_commits({ path = vim.fn.expand("%:p") })
end, { desc = "Git Log this File" })
keymap.set("n", "<leader>gl", "<cmd>terminal lazygit<cr>", { noremap = true, silent = true, desc = "Lazygit" })
keymap.set("n", "<leader>gp", "<cmd>terminal git pull<cr>", { noremap = true, silent = true, desc = "Git Push" })
keymap.set("n", "<leader>gs", "<cmd>terminal git push<cr>", { noremap = true, silent = true, desc = "Git Pull" })
keymap.set("n", "<leader>ga", "<cmd>terminal git add .<cr>", { noremap = true, silent = true, desc = "Git Add All" })
keymap.set(
	"n",
	"<leader>gc",
	'<cmd>terminal git commit -m "Autocommit from nvim"<cr>',
	{ noremap = true, silent = true, desc = "Git Autocommit" }
)
-- Toggle to see last session result. Without this, you can't see session output in case of unhandled exception.
vim.keymap.set("n", "<F7>", dapui.toggle, { desc = "Debug: See last session result." })

-- Slightly advanced example of overriding default behavior and theme
vim.keymap.set("n", "<leader>fz", function()
	builtin.current_buffer_fuzzy_find(require("telescope.themes").get_dropdown({
		winblend = 10,
		previewer = false,
	}))
end, { desc = "[/] Fuzzily search in current buffer" })

vim.keymap.set("n", "<leader>s/", function()
	builtin.live_grep({
		grep_open_files = true,
		prompt_title = "Live Grep in Open Files",
	})
end, { desc = "[S]earch [/] in Open Files" })

-- Searching through the entire config
vim.keymap.set("n", "<leader>sn", function()
	builtin.find_files({ cwd = vim.fn.stdpath("config") })
end, { desc = "[S]earch [N]eovim files" })
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
