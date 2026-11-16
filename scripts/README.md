# scripts

The launch script and prompts for the local language model that codes the reference set and assigns its indexing terms.

- `launch_rds_llm.sh` starts an Ollama container on one or more GPUs and loads a model into it. It prints the Ollama version and the model's digest. Models are stored in the folder `MODELS_DIR` names; set it to your own model folder before running.
- `coding_prompt.md` is the prompt the model receives for each reference set source, with the source's title and abstract filled in at `{title}` and `{abstract}`. Its fields and values come from the PCC table in `research-protocol.qmd`, the Criteria and factor themes in `materials/screening-guide.qmd`, and `codebook.yml`.
- `indexing_prompt.md` is the prompt the model receives with the MeSH headings, author keywords and OpenAlex keywords of the development set sources, filled in at `{terms}`. Each MeSH heading carries its NLM scope note. Its values are the Practice values and factors in `coding_prompt.md`.
