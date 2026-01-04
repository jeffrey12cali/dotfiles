return {
    "stevearc/conform.nvim",
    event = { "BufWritePre" },
    cmd = { "ConformInfo" },
    keys = {
        {
            -- Customize or remove this keymap to your liking
            "<leader>f",
            function()
                require("conform").format({ async = true })
            end,
            mode = "",
            desc = "Format buffer",
        },
    },
    -- This will provide type hinting with LuaLS
    ---@module "conform"
    ---@type conform.setupOpts
    opts = function()
        local util = require("conform.util")
        return {
        -- Define your formatters
        formatters_by_ft = {
            javascript = { "prettier", stop_after_first = true },
            javascriptreact = { "prettier", stop_after_first = true },
            typescript = { "prettier", stop_after_first = true },
            typescriptreact = { "prettier", stop_after_first = true },
            json = { "prettier", stop_after_first = true },
            python = { "isort", "black" },
        },

        -- Only run formatters when a project config is present
        formatters = {
            prettier = {
                condition = util.root_file({
                    ".prettierrc",
                    ".prettierrc.json",
                    ".prettierrc.js",
                    ".prettierrc.cjs",
                    ".prettierrc.mjs",
                    ".prettierrc.yaml",
                    ".prettierrc.yml",
                    "prettier.config.js",
                    "prettier.config.cjs",
                    "prettier.config.mjs",
                }),
            },
            black = {
                condition = util.root_file({
                    "pyproject.toml",
                    "black.toml",
                }),
            },
            isort = {
                condition = util.root_file({
                    "pyproject.toml",
                    "setup.cfg",
                    "tox.ini",
                    ".isort.cfg",
                }),
            },
        },

        -- Set up format-on-save, but never fall back to LSP formatting
        format_on_save = { timeout_ms = 500, lsp_format = "never" },
        notify_on_error = false,
        }
    end,
    init = function()
        -- If you want the formatexpr, here is the place to set it
        vim.o.formatexpr = "v:lua.require'conform'.formatexpr()"
    end,
}
