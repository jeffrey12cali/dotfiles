return {
    'VonHeikemen/lsp-zero.nvim',
    branch = 'v3.x',
    dependencies = {
        --- Uncomment the two plugins below if you want to manage the language servers from neovim
        { 'williamboman/mason.nvim' },
        { 'williamboman/mason-lspconfig.nvim' },

        -- LSP Support
        { 'neovim/nvim-lspconfig' },
        -- Autocompletion
        { 'hrsh7th/nvim-cmp' },
        { 'hrsh7th/cmp-nvim-lsp' },
        { 'L3MON4D3/LuaSnip' },
    },
    config = function()
        local lsp = require("lsp-zero")

        require('mason').setup({})
        require('mason-lspconfig').setup({
            ensure_installed = {
                'ts_ls',
                'eslint',
                'lua_ls',
                'ruff',
                'basedpyright',
            }
        })

        local cmp = require('cmp')
        local cmp_select = { behavior = cmp.SelectBehavior.Select }
        local cmp_mappings = lsp.defaults.cmp_mappings({
            ['<C-p>'] = cmp.mapping.select_prev_item(cmp_select),
            ['<C-n>'] = cmp.mapping.select_next_item(cmp_select),
            ['<Tab>'] = cmp.mapping.select_next_item(cmp_select),
            ['<C-y>'] = cmp.mapping.confirm({ select = true }),
            ["<C-Space>"] = cmp.mapping.complete(),
        })

        cmp.setup({
            sources = {
                { name = 'nvim_lsp' },
            },
            mapping = cmp_mappings
        })

        -- Create (or clear) the LspFormatting group once
        local formatting_group = vim.api.nvim_create_augroup("LspFormatting", { clear = true })

        vim.api.nvim_create_autocmd("LspAttach", {
            group = vim.api.nvim_create_augroup('lsp_attach_disable_ruff_hover', { clear = true }),
            callback = function(args)
                local client = vim.lsp.get_client_by_id(args.data.client_id)
                if client == nil then
                    return
                end
                if client.name == 'ruff' then
                    -- Disable hover in favor of Pyright
                    client.server_capabilities.hoverProvider = false
                end
            end,
            desc = 'LSP: Disable hover capability from Ruff',
        })

        lsp.on_attach(function(client, bufnr)
            -- Enable formatting only for clients that support it
            if client.supports_method("textDocument/formatting") then
                -- Clear existing autocmds in this group to avoid duplicates
                vim.api.nvim_clear_autocmds({ group = formatting_group, buffer = bufnr })
                -- Create a new autocmd that formats on save
                vim.api.nvim_create_autocmd("BufWritePre", {
                    group = "LspFormatting",
                    buffer = bufnr,
                    callback = function()
                        vim.lsp.buf.format({ bufnr = bufnr })
                    end,
                })
            end
            local opts = { buffer = bufnr, remap = false }

            vim.keymap.set("n", "gd", function() vim.lsp.buf.definition() end, opts)
            vim.keymap.set("n", "K", function() vim.lsp.buf.hover() end, opts)
            vim.keymap.set("n", "<leader>vws", function() vim.lsp.buf.workspace_symbol() end, opts)
            vim.keymap.set("n", "<leader>vd", function() vim.diagnostic.open_float() end, opts)
            vim.keymap.set("n", "[d", function() vim.diagnostic.goto_next() end, opts)
            vim.keymap.set("n", "]d", function() vim.diagnostic.goto_prev() end, opts)
            vim.keymap.set("n", "<leader>vca", function() vim.lsp.buf.code_action() end, opts)
            vim.keymap.set("n", "<leader>vrr", function() vim.lsp.buf.references() end, opts)
            vim.keymap.set("n", "<leader>vrn", function() vim.lsp.buf.rename() end, opts)
            vim.keymap.set("i", "<C-h>", function() vim.lsp.buf.signature_help() end, opts)
        end)

        lsp.setup()
    end
}
