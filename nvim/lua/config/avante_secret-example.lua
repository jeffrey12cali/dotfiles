return {
    provider = "ollama",
    vendors = {
        ollama = {
            __inherited_from = "openai",
            api_key_name = "",
            endpoint = "http://192.168.122.1:11430/v1",
            model = "llama3.1:8b-instruct-q4_0_8k",
        },
    },
}
