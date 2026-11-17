# prompts

The prompts for the local language model that codes the reference set and assigns its indexing terms. `scripts/launch_rds_llm.sh`, at the repo root, starts the model.

- `coding_prompt.md` is the prompt the model receives for each reference set source, with the source's title and abstract filled in at `{title}` and `{abstract}`. Its fields and values come from the PCC table in `research-protocol.qmd`, the Criteria and factor themes in `materials/screening-guide.qmd`, and `codebook.yml`.
- `indexing_prompt.md` is the prompt the model receives for each distinct MeSH heading, author keyword and OpenAlex keyword of the reference set, one term at a time, filled in at `{term}` with its type. A MeSH heading carries its NLM scope note. Its values are the Practice values and factors in `coding_prompt.md`.
