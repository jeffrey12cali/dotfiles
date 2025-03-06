return {
    'numToStr/Comment.nvim',
    config = function ()
        require('Comment').setup({
            ---LHS of toggle mappings in NORMAL mode
            toggler = {
                ---Block-comment toggle keymap
                block = 'gwc',
            },
            ---LHS of operator-pending mappings in NORMAL and VISUAL mode
            opleader = {
                ---Block-comment keymap
                block = 'gw',
            },
        })
    end
}
