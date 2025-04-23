local helpers = require("config.helpers")

local nmap = helpers.nmap
local noremap = helpers.noremap
local vnoremap = helpers.vnoremap
local xnoremap = helpers.xnoremap
local map = vim.api.nvim_set_keymap

local opts = { noremap = true, silent = true }
local keymap = vim.keymap

-- keymap.set("n", "<leader>sv", "<C-w>v") -- split window vertically
-- keymap.set("n", "<leader>sh", "<C-w>s") -- split window horizontally
-- keymap.set("n", "<leader>se", "<C-w>=") -- make split windows equal width & height
-- keymap.set("n", "<leader>sx", ":close<CR>") -- close current split window
--
-- keymap.set("n", "<leader>to", ":tabnew<CR>") -- open new tab
-- keymap.set("n", "<leader>tx", ":tabclose<CR>") -- close current tab
-- keymap.set("n", "<leader>tn", ":tabn<CR>") --  go to next tab
-- keymap.set("n", "<leader>tp", ":tabp<CR>") --  go to previous tab
-- keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>")
-- -- Diagnostic keymaps
-- keymap.set("n", "[d", vim.diagnostic.goto_prev, { desc = "Go to previous [D]iagnostic message" })
-- keymap.set("n", "]d", vim.diagnostic.goto_next, { desc = "Go to next [D]iagnostic message" })
-- keymap.set("n", "<leader>e", vim.diagnostic.open_float, { desc = "Show diagnostic [E]rror messages" })
-- keymap.set("n", "<leader>q", vim.diagnostic.setloclist, { desc = "Open diagnostic [Q]uickfix list" })
--
-- keymap.set("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })
--
-- Disable arrow keys in normal mode
keymap.set("n", "<left>", '<cmd>echo "Use h to move!!"<CR>')
keymap.set("n", "<right>", '<cmd>echo "Use l to move!!"<CR>')
keymap.set("n", "<up>", '<cmd>echo "Use k to move!!"<CR>')
keymap.set("n", "<down>", '<cmd>echo "Use j to move!!"<CR>')

-- Keybinds to make split navigation easier.
--
-- keymap.set("n", "<S-h>", "<C-w><C-h>", { desc = "Move focus to the left window" })
-- keymap.set("n", "<S-l>", "<C-w><C-l>", { desc = "Move focus to the right window" })
-- keymap.set("n", "<S-j>", "<C-w><C-j>", { desc = "Move focus to the lower window" })
-- keymap.set("n", "<S-k>", "<C-w><C-k>", { desc = "Move focus to the upper window" })
-- --
-- keymap.set("n", "<C-,>", "<cmd>BufferPrevious<CR>")
--
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
