# scripts

The launch script for a local language model.

- `launch_rds_llm.sh` starts an Ollama container on one or more GPUs and loads a model into it. It prints the Ollama version and the model's digest. Models are stored in the folder `MODELS_DIR` names; set it to your own model folder before running.
