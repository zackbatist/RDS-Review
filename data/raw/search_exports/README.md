# search_exports

One file per database search, exactly as exported. Do not edit these files.

## File names

`<database>_<YYYY-MM-DD>[_<block>].<ext>`

- `database` is the database name in lowercase, with hyphens for spaces.
- The date is the search date.
- `block` is `A` or `B`, as defined in `materials/search-strategy.qmd`.
- Supported formats are `.ris` and `.csv`.

Examples: `scopus_2026-11-02_A.ris`, `web-of-science_2026-11-02_B.ris`.

Supplementary sources, such as citation searching, use the prefix `other-`: `other-citation-searching_2026-12-01.ris`.

## CSV columns

CSV exports need a title column. These columns are recognized, ignoring case: `Title`, `Abstract`, `Authors`, `Year`, `Journal`, `DOI`. Common variants such as `Source title` and `Publication year` are also recognized.
