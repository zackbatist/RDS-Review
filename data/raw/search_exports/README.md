# search_exports

One file per database search, exactly as exported. Do not edit these files, and keep the exports of earlier searches in this folder. A record keeps its `record_id` across searches only while the earlier exports stay here.

## File names

`<database>_<YYYY-MM-DD>[_<block>].<ext>`

- `database` is the database name in lowercase, with hyphens for spaces.
- The date is the search date.
- `block` is `A` or `B`, as defined in `materials/search-strategy.qmd`.
- Supported formats are `.ris` and `.csv`.

Examples: `scopus_2026-11-02_A.ris`, `web-of-science_2026-11-02_B.ris`.

Supplementary sources, such as citation searching, use the prefix `other-`: `other-citation-searching_2026-12-01.ris`.

## CSV columns

CSV exports need a title column. These columns are recognized, ignoring case: `Title`, `Abstract`, `Authors`, `Year`, `Journal`, `DOI`, `Volume`, `Issue`, and `Pages`. Common variants such as `Source title`, `Publication year`, and `Page start` with `Page end` are also recognized. Separate several authors with semicolons.

Volume, issue, and pages help to match records that have no DOI, so keep them when you export.

## Duplicate decisions

`data/raw/dedup_decisions.csv` is optional and is not an export. A reviewer writes it to settle pairs of records that the automatic matching got wrong or left open. It has the columns `member_a`, `member_b`, and `decision` (`merge` or `separate`). The member identifiers, such as `scopus_2026-11-02_A.ris#14`, are listed in `data/processed/duplicate_groups.csv` and `data/processed/possible_duplicates.csv`.
