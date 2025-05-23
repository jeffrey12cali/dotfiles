return {
    behaviour = {
        use_cwd_as_project_root = true,
    },
    provider = "ollama",
    ollama = {
        endpoint = "http://127.0.0.1:11430", -- Note that there is no /v1 at the end.
        model = "gemma3:12b-it-q4_K_M",
    },
}
