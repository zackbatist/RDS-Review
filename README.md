# RDS-Review

A scoping review of the factors that influence the sharing and reuse of research data. It centres on health research data and compares it with other fields. The site is built with Quarto.

Site: <https://zackbatist.info/RDS-Review/>

## Preview the site locally

1. Install [Quarto](https://quarto.org/).
2. Clone this repository and `cd` into it.
3. Create a virtual environment outside any synced folder and install the Python packages:

   ```bash
   python3 -m venv ~/.venvs/rds-review
   source ~/.venvs/rds-review/bin/activate
   pip install -r requirements.txt
   ```

4. Run `quarto preview`.
5. Open `localhost:7777` in a web browser.

## Publish

Run `quarto publish gh-pages`.

## Layout

| Path | Contents |
| --- | --- |
| `index.qmd`, `research-protocol.qmd`, `codebook.qmd` | Home page, protocol, and charting form |
| `codebook.yml` | The charting variables, their allowed values, and the exclusion reason codes. The codebook page and the notebooks read it. |
| `materials/` | Search strategy, screening guide, and checklists |
| `data/raw/` | Search exports, screening exports, and charted data as entered, and in `search-development/` what the search development scripts and the local model return. Notebooks never change these. |
| `data/processed/` | Files written by the notebooks |
| `analysis/` | The notebooks and their index page |
| `analysis/00_search-development/` | The search development plan, notebook 00, the scripts that call the database APIs, the scripts and prompts for the local model, the log, and the summary of outcomes |
| `scripts/` | The launch script for a local language model |
| `assets/` | Bibliography and citation style |

Notebook inputs, outputs, and run order are on the Analysis page of the site.
