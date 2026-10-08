# screening_exports

Decisions exported from the screening tool, as CSV files with lowercase values.

`title_abstract.csv` has the columns `record_id` and `decision` (`include` or `exclude`). It has one row for every record in `data/processed/deduplicated_records.csv`.

`full_text.csv` has the columns `record_id`, `source_id` (optional), `retrieved` (`yes` or `no`), `decision` (`include` or `exclude`, blank when not retrieved), and `reason` (an exclusion reason code from `codebook.yml`). It has one row for every record included at title and abstract.

These two files hold the final decisions, with disagreements between reviewers already settled. They are the only files the counts use.

## Reviewer files (optional)

When more than one person screens, add each reviewer's own decisions: `title_abstract_<reviewer>.csv` and `full_text_<reviewer>.csv`, for example `title_abstract_r1.csv`. They have the columns `record_id` and `decision`, and they may cover only a sample. The notebook reports percent agreement and Cohen's kappa for each pair of reviewers.

`record_id` values come from `data/processed/deduplicated_records.csv`. Reason codes and the full format are in `materials/screening-guide.qmd`.
