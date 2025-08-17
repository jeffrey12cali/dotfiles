return {
    "nvimtools/none-ls.nvim",             -- or "jose-elias-alvarez/null-ls.nvim"
    dependencies = { "williamboman/mason.nvim" },
    event = { "BufReadPre", "BufNewFile" },
    config = function()
        local null_ls = require("null-ls")
        null_ls.setup({
            sources = {
                -- only attach Black to Python files
                null_ls.builtins.formatting.black.with({
                    filetypes = { "python" },
                }),
                -- only attach isort to Python files
                null_ls.builtins.formatting.isort.with({
                    filetypes = { "python" },
                }),
            },
            -- you can debug if things don’t fire:
            debug = false,
        })
    end,
}
