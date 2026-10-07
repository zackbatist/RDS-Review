# screening_exports

Decisions exported from the screening tool, as two CSV files with lowercase values.

`title_abstract.csv` has the columns `record_id` and `decision` (`include` or `exclude`).

`full_text.csv` has the columns `record_id`, `source_id` (optional), `retrieved` (`yes` or `no`), `decision` (`include` or `exclude`, blank when not retrieved), and `reason` (an exclusion reason code).

`record_id` values come from `data/processed/deduplicated_records.csv`. Reason codes and the full format are in `materials/screening-guide.qmd`.
