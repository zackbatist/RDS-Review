# Search development log

Work on the plan in `notes/2026-11-11-search-development-plan.qmd`, run unattended on the night of 11 to 12 November 2026.

## Step 1. Comparability assessment: done

### Reference set

- **Selection.** 97 references cited as findings in sections 4 and 5 and Table 2 of Chawinga and Zinn (2019), against their stated 105. `reference_sources.csv` records the section and page where each is cited (`cited_at`).
- **Left out as background:** Gupta (2013) and Steen (2011), cited in 5.4.1 for research fraud in general; Higgins (2011), cited in 5.5.1.1 and 5.5.2.1 for data sharing being an emerging concept; Rowhani-Farid and Barnett (2016), cited only in the literature review (section 2.3).
- **Kept although Chawinga and Zinn's own criteria exclude them:** news items, editorials, letters, a press release (European Commission 2012), a webinar (Guedon 2015) and a blog post (Mundel 2014). They are cited as findings or listed in Table 2, so they belong to the set Chawinga and Zinn report.
- **Verification.** DOIs were verified through PubMed (36 sources) and OpenAlex (33 sources), not Crossref. Crossref and OpenAlex batch queries failed through the fetch tool (URL length limits and dropped filters), and the shell can't reach either API. OpenAlex resolves DOIs from Crossref metadata, so a DOI that resolves there is a registered DOI. Two JSTOR DOIs (Anderson and Schonfeld 2009, Cahill and Passamano 2007) could not be fetched; they are kept with the DOIs Chawinga and Zinn give. 26 references have no DOI (theses, reports, grey literature, some older articles) and carry title, year and venue only.
- **Year.** Earliest publication date from PubMed or OpenAlex. Four sources date earlier than Chawinga and Zinn cite them, because they appeared online first: Bezuidenhout (cited 2013, online 2011), Harding et al. (cited 2013, online 2011), Mennes et al. and Van Horn and Gazzaniga (cited 2013, online 2012). Koltay (cited 2017) appeared online in 2015.
- **Split.** 56 sources in the development set (2007 to 2014) and 41 in the test set (2015 to 2018), matching Fig. 4's 64 and 41 closely.

### Coding

- **Text used.** PubMed abstracts for 33 sources, OpenAlex abstracts for 27, and titles alone for 37 (no abstract reachable: theses, reports, grey literature, and articles OpenAlex holds without an abstract). `abstract_source` in `reference_sources.csv` records which. No full texts were read; every `location` is *title* or *abstract*.
- **OpenAlex passages.** OpenAlex stores abstracts as word-position indexes, and the fetch tool returns only short quoted clauses from them, so OpenAlex passages are clauses, not whole sentences, and a few carry small reconstruction gaps the tool flagged (Dai et al. 2018, Peng et al. 2016, Parr 2007, Ostell 2009).
- **Title-only codes.** For the 37 title-only sources, Factors is *none* where the title names no factor on the list. Eleven sources concern sharing or reuse but fall out as `not-factors` on their titles alone: Cahill and Passamano 2007, Delson et al. 2007, Nelson 2009, Levenson 2010, Kowalczyk and Shankar 2011, Albert 2012, Perrino et al. 2013, Mundel 2014, Curty 2015, Jeng et al. 2016, Chen and Wu 2017. Their abstracts or full texts may well report factors. `counts.csv` gives the number of codes resting on no passage.
- **Judgments worth checking:**
  - Plengsaeng et al. (2014): water management data shared between agencies. First coded *not-research-data*; recoded `data_origin` *unclear* and Reason *other* after commit d5a6f96 limited `not-research-data` to public health, health systems and clinical care data. No `data_origin` value covers operational data outside health.
  - Anane-Sarpong et al. (2017), Chandramohan et al. (2008), Kostkova (2018): health and demographic surveillance data used in research, coded *reused*.
  - Sheather (2009): patient health information in care, coded *not-research-data*.
  - Neuroimaging, genetics and computational neuroscience sources coded `field` *health*; biology, ecology and biodiversity sources coded *other*.

### Comparison

- `comparison.csv` uses one relation value beyond the plan's three: *narrower*, where Chawinga and Zinn's criterion admits only part of what the RDS-Review criterion admits (source type, empirical design, language). The plan's *overlap* assumes each side admits sources the other excludes, which doesn't hold for these three.

### Search statements

- `statement_matches.csv` matches Chawinga and Zinn's four statements against titles and recorded passages, with and without keywords. Full abstracts weren't stored, so these counts are lower bounds. Read as separate words, the four statements reach at most 27 of the 97 sources, consistent with the paper's account that most sources came from citation tracking and Google Scholar. "digital curation AND data sharing" matches none.

### Verdict

All seven PCC parts are *covered*. Reuse rests on 6 development and 4 test sources eligible apart from year; tier 1 (health) rests on 15 development and 8 test sources.

## Step 2. Terms by PCC part: done

- **Sources.** All 56 development set sources.
- **Term types pulled.** Recorded terms from `reference_codes.csv`; MeSH headings and author keywords from PubMed for the 21 PubMed-indexed development sources; OpenAlex keywords for the development sources fetched through OpenAlex. OpenAlex keywords were not pulled for PubMed-indexed sources, to save fetches; the hybrid notebook pulls them for every source.
- **Assignment.** I placed MeSH headings and keywords under PCC parts by meaning. The mapping is in `/home/claude/scripts/step2.py` (dictionaries `MESH` and `KW`) and in each row's `assignment_basis`. I did not retrieve NLM scope notes, so the basis for MeSH rows says so; the hybrid notebook pulls them from NLM. "Information Dissemination" and "Access to Information" go under *sharing*; "Cooperative Behavior", "Databases, Factual" and similar headings match no PCC part and are left out.
- **Normalisation.** Lowercase, hyphens to spaces, plural and ending variants merged. Single-word terms are truncated on their shared stem when the stem has five or more letters (`barrier*`, `challeng*`, `incentiv*`, `obstacl*`).
- **MeSH explosion.** All MeSH terms search as `[mh:noexp]`. I did not check narrower headings, so none qualifies for `[mh]` yet.
- **Selection.** *Sharing* and *reuse* terms all pass to step 3 (37 and 9 in PubMed; 35 and 9 in Scopus and Web of Science, after the Enke fix). Factor terms were selected per theme by the rule in the plan and carry the status *to screening*.
- **Recorded terms are long.** Many recorded *sharing* terms are phrases lifted from passages ("sharing of health data", "openly archiving raw research data"). Step 3's yield rule will drop most of them, since a phrase matching one development source rarely meets the threshold; that is the rule doing its job.
- **No fallback needed.** *Reuse* has 9 candidate terms from 6 development sources.

## Step 3. Command blocks: written, not run

- **File.** `step3_blocks.md`: 1 keys file, 2 environment, 3 check files, 4 API test, 5 to 7 query blocks (one per database), 8 to 10 precision blocks.
- **Repository path assumed** to be `~/RDS-Review`. Change the `cd` line in every block if not.
- **Environment.** The blocks use the environment the RDS-Review README sets out, `~/.venvs/rds-review`, installed from `requirements.txt`, which now includes `requests==2.34.2`.
- **Outputs follow the plan.** Each query block writes `query_runs_<database>.csv` and `load_<database>.csv`, replaces its database's rows in `query_tests.csv` and `query_misses.csv`, and fills the step 3 columns of its database's *sharing* and *reuse* rows in `terms.csv`. Each precision block writes `precision_sample_<database>.csv` and records the seed in `query_tests.csv`. The precision columns of `query_tests.csv` stay empty until the screened samples come back; `analysis/00-search-development.ipynb` computes precision from the screened samples.
- **Database names in file names** are `pubmed`, `scopus` and `web-of-science`, the names `data/raw/search_exports/README.md` uses.
- **No API exports in `data/raw/search_exports/`.** The API loads hold identifiers, DOIs, titles and years only, and `01-deduplication.ipynb` needs full records exactly as exported. The review's exports come from each database's own interface as RIS files once the queries are settled.
- **README to update.** `data/raw/search_exports/README.md` still names the `query` part of a file name as `q1` to `q4`, the four queries this work replaces.
- **Checks done here.** Every embedded Python block compiles. The query and precision logic ran end to end against mocked API responses, and `analysis/00-search-development.ipynb` ran on the mocked results; the real APIs are untested until block 4 runs on citf-analysis.
- **Candidates deduplicated on written form.** Where two terms write the same search string in a database (a recorded term and an author keyword, say), the query block tests it once, and both rows in `terms.csv` get its results.
- **Draft ties.** Highest added yield first, then fewer records added, then alphabetical.
- **Precision seed** 20261112, fixed in the block. PubMed records take their abstracts from PubMed, then OpenAlex, then Crossref; Scopus and Web of Science records from OpenAlex, then Crossref.
- **Web of Science** uses the Starter API (`DO=` for DOIs, `TS=` for topic, `PY=` for years). If the subscription is the Expanded API, the endpoint and field names in `wos_search` and `wos_records` change.
- **Fix after step 2.** Enke et al. (2012)'s recorded Practice term had a stray clause ("biodiversity data sharing; use"); corrected to "biodiversity data sharing" in `reference_codes.csv`, and `terms.csv` and `term_syntax.csv` regenerated.

## Notebooks

- **`analysis/00-search-development.ipynb`** reads every file in `data/search_tests/` and shows the outcomes of steps 1 to 3, in the form of notebooks 01 to 04. It checks that the files agree with each other before it shows anything, and shows step 3 once `query_tests.csv` exists. It writes nothing.
- **`search-development-hybrid.ipynb`**, kept outside the repo, runs steps 1 to 3 with the API calls and computation in code, and three marked hand-offs: I code the sources and assign indexing terms to PCC parts by meaning, and the reviewers screen the precision samples. It adds a Crossref check of every DOI, OpenAlex keywords for every source and NLM scope notes for every MeSH heading (`mesh_scope_notes.csv`). Run offline on the overnight files, it reproduces `counts.csv`, `verdict.csv` and `term_syntax.csv` exactly. Its API cells have not run.
- **New input.** `reference_candidates.csv`: the 97 candidates with `cited_at`, which the hybrid notebook starts from.

## Changes after commit d5a6f96

- **Precision screening.** The reviewers screen the precision samples, so no language model makes a decision about records the review may include. Plan item 10 now says so, and the Artificial intelligence section of `research-protocol.qmd` states my role in coding the reference set.
- **`data_origin` values.** `codebook.yml` now lists the plan's values, `research`, `not-research-data`, `reused`, `mixed` and `unclear`, with their definitions. `codebook.qmd` and `materials/screening-guide.qmd` print the codebook, so both need rendering again.
- **Plengsaeng et al. (2014)** recoded, as noted under Judgments worth checking; `counts.csv` regenerated. The verdict and the in-scope count are unchanged.

## To do

- **Artificial intelligence section of `research-protocol.qmd`.** The sentence "The query terms come from those codes." oversimplifies how the terms were selected. Rewrite it once step 3 has run, so it states the exact outcomes: which terms entered each query and how the yield, coverage and precision tests decided them.
