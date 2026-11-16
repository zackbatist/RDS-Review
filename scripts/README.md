# scripts

The launch script for a local language model.

- `launch_rds_llm.sh` starts a llama.cpp server on one or more GPUs and loads a model into it. Each model it knows is a GGUF file on Hugging Face, fixed by repository, revision and SHA-256: `qwen3.5-122b` is unsloth's Q4_K_M build of Qwen3.5-122B-A10B, and `qwen3.8-27b` is unsloth's UD-Q4_K_M build of Qwen3.8-27B. The script downloads the files on first use, checks their SHA-256 every time, and stores them in the folder `MODELS_DIR` names, by default `~/models`. It runs the llama.cpp server image whose build `LLAMACPP_BUILD` names, by default b12375, the newest CUDA 12 build on 16 November 2026, with the context length `CTX` names, by default 16,384 tokens. Once the model is loaded, it prints the model's repository, revision and checksums, the image's digest, the server's build and its context length.
