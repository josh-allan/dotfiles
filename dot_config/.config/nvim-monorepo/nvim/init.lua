if vim.env.VSCODE then
  vim.g.vscode = true
else
  require("base.lazy")
end
