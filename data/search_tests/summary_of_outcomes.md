# Search development outcomes

Outcomes of the plan in `notes/2026-11-11-search-development-plan.qmd`, as of 12 November 2026. Steps 1 and 2 are done; step 3 has not run yet. `log.md` records every judgment call behind these figures.

## Step 1. Comparability assessment

**Reference set.** The reference set holds 97 references Chawinga and Zinn (2019) cite as findings in sections 4 and 5 and Table 2, against the 105 they report. The development set holds 56 sources (2007 to 2014); the test set holds 41 (2015 to July 2018).

**Eligibility.** 65 sources are eligible apart from year (39 development, 26 test). 26 sources are in scope, all in the test set, since the review period starts in 2015. Exclusion codes across the 71 sources out of scope: *date* 39, *not-data-sharing* 18, *not-factors* 12, *not-research-data* 1, *other* 1.

**Verdict.** `verdict.csv` marks all seven PCC parts *covered* in both sets. *Reuse* rests on 6 development and 4 test sources; *stakeholder perspectives* on 5 development sources.

**Title-only coding.** 37 sources carry codes from their titles alone, because no abstract was reachable. Eleven of them fall out as *not-factors* on their titles, and their abstracts may report factors. The notebook pulls abstracts from Crossref, OpenAlex and PubMed, and its coding can overturn these.

**Chawinga and Zinn's search statements.** `statement_matches.csv` shows their four statements reach at most 27 of the 97 sources, and "digital curation AND data sharing" reaches none. Their statements account for a minority of what they included, consistent with their account of finding most sources through citation tracking and Google Scholar. They offer no template for the RDS-Review queries.

## Step 2. Terms by PCC part

**Candidates for step 3.** `terms.csv` lists 37 *sharing* and 9 *reuse* terms for PubMed, and 35 *sharing* and 9 *reuse* terms each for Scopus and Web of Science.

**Strongest terms.** For *sharing*, MeSH "Information Dissemination" and the recorded term "data sharing" each match 16 development sources. For *reuse*, the strongest term, "data reuse", matches 2.

**Factor terms.** Factor terms carry the status *to screening*. They inform screening and stay out of the queries.

**Recorded terms.** Many recorded terms are long phrases lifted from passages. Step 3's yield rule will drop most of them.

## Step 3. Query tests

`step3_blocks.md` holds the paste-ready blocks for citf-analysis. They have not run. They write:

- `query_tests.csv`: per database, the final query, development yield, load for 2015 to 2025, test set coverage with 95% CI, and the precision sample's seed
- `query_misses.csv`: indexed test set sources each final query misses, and development set sources reached only by terms excluded by yield
- `terms.csv`: development yield, load, sources added and status for every *sharing* and *reuse* term
- `query_runs_<database>.csv`: every term run, the threshold, each draft addition and each trim drop
- `load_<database>.csv`: the records each final query returns for 2015 to 2025
- `precision_sample_<database>.csv`: 100 records per database, which the reviewers screen for precision

*Reuse* carries the main risk. Few reference sources support it, so a query the reference set judges complete can still miss reuse-heavy records.

## Notebook

`analysis/00-search-development.ipynb` reads every file in `data/search_tests/` and shows these outcomes, with step 3 and precision once their files exist.
