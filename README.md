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
| `materials/` | Search strategy, screening guide, and checklists |
| `data/raw/` | Search exports, screening exports, and charted data as entered. Notebooks never change these. |
| `data/processed/` | Files written by the notebooks |
| `analysis/` | The four notebooks and their index page |
| `assets/` | Bibliography and citation style |

Notebook inputs, outputs, and run order are on the Analysis page of the site.
