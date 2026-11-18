# Search development log

Work on the plan in `index.qmd`, run unattended on the night of 11 to 12 November 2026.

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

- **File.** `step3_blocks.md`, since replaced by the scripts in `retrieval/`: 1 keys file, 2 environment, 3 check files, 4 API test, 5 to 7 query blocks (one per database), 8 to 10 precision blocks.
- **Repository path assumed** to be `~/RDS-Review`. Change the `cd` line in every block if not.
- **Environment.** The blocks use the environment the RDS-Review README sets out, `~/.venvs/rds-review`, installed from `requirements.txt`, which now includes `requests==2.34.2`.
- **Outputs follow the plan.** Each query block writes `query_runs_<database>.csv` and `load_<database>.csv`, replaces its database's rows in `query_tests.csv` and `query_misses.csv`, and fills the step 3 columns of its database's *sharing* and *reuse* rows in `terms.csv`. Each precision block writes `precision_sample_<database>.csv` and records the seed in `query_tests.csv`. The precision columns of `query_tests.csv` stay empty until the screened samples come back; `analysis/00-search-development.ipynb` computes precision from the screened samples.
- **Database names in file names** are `pubmed`, `scopus` and `web-of-science`, the names `data/raw/search_exports/README.md` uses.
- **No API exports in `data/raw/search_exports/`.** The API loads hold identifiers, DOIs, titles and years only, and `01-deduplication.ipynb` needs full records exactly as exported. The review's exports come from each database's own interface as RIS files once the queries are settled.
- **README to update.** `data/raw/search_exports/README.md` still names the `query` part of a file name as `q1` to `q4`, the four queries this work replaces.
- **Checks done here.** Every embedded Python block compiles. The query and precision logic ran end to end against mocked API responses, and `00-search-development.ipynb` ran on the mocked results; the real APIs are untested until block 4 runs on the analysis server.
- **Candidates deduplicated on written form.** Where two terms write the same search string in a database (a recorded term and an author keyword, say), the query block tests it once, and both rows in `terms.csv` get its results.
- **Draft ties.** Highest added yield first, then fewer records added, then alphabetical.
- **Precision seed** 20261112, fixed in the block. PubMed records take their abstracts from PubMed, then OpenAlex, then Crossref; Scopus and Web of Science records from OpenAlex, then Crossref.
- **Web of Science** uses the Starter API (`DO=` for DOIs, `TS=` for topic, `PY=` for years). If the subscription is the Expanded API, the endpoint and field names in `wos_search` and `wos_records` change.
- **Fix after step 2.** Enke et al. (2012)'s recorded Practice term had a stray clause ("biodiversity data sharing; use"); corrected to "biodiversity data sharing" in `reference_codes.csv`, and `terms.csv` and `term_syntax.csv` regenerated.

## Notebooks

- **`00-search-development.ipynb`** reads every file in `data/raw/search-development/` and `data/processed/search-development/` and shows the outcomes of steps 1 to 3, in the form of notebooks 01 to 04. It checks that the files agree with each other before it shows anything, and shows step 3 once `query_tests.csv` exists. It writes nothing.
- **`search-development-hybrid.ipynb`**, kept outside the repo, runs steps 1 to 3 with the API calls and computation in code, and three marked hand-offs: I code the sources and assign indexing terms to PCC parts by meaning, and the reviewers screen the precision samples. It adds a Crossref check of every DOI, OpenAlex keywords for every source and NLM scope notes for every MeSH heading (`mesh_scope_notes.csv`). Run offline on the overnight files, it reproduces `counts.csv`, `verdict.csv` and `term_syntax.csv` exactly. Its API cells have not run.
- **New input.** `reference_candidates.csv`: the 97 candidates with `cited_at`, which the hybrid notebook starts from.

## Changes after commit d5a6f96

- **Precision screening.** The reviewers screen the precision samples, so no language model makes a decision about records the review may include. Plan item 10 now says so, and the Artificial intelligence section of `research-protocol.qmd` states my role in coding the reference set.
- **`data_origin` values.** `codebook.yml` now lists the plan's values, `research`, `not-research-data`, `reused`, `mixed` and `unclear`, with their definitions. `codebook.qmd` and `materials/screening-guide.qmd` print the codebook, so both need rendering again.
- **Plengsaeng et al. (2014)** recoded, as noted under Judgments worth checking; `counts.csv` regenerated. The verdict and the in-scope count are unchanged.

## Step 3, first run: PubMed and Scopus, 12 November 2026

- **Results** (commit ffd382a). PubMed: `("data sharing"[tiab]) OR ("sharing data"[tiab])`, load 9,857, coverage 11 of 12 indexed test set sources. Scopus: `(TITLE-ABS-KEY("data sharing")) OR (TITLE-ABS-KEY("sharing of health data"))`, load 36,067, coverage 20 of 26, and 18 of 19 In scope. Web of Science waits on Clarivate's approval of the key.
- **No reuse term passed the yield rule.** Every development set source coded *reuse* is coded *both*, so "data sharing" retrieves them and no reuse term adds sources. The test set holds one testable source coded *reuse* alone (Curty 2017), too few to test reuse coverage.
- **Recorded phrases favoured by the yield rule.** A recorded phrase always finds the source it came from, so a narrow phrase can pass the threshold on one source at almost no cost: "sharing of health data" entered the Scopus query on Haddow (2011) for 10 records.
- **Loads included all of 2026.** PubMed returned 1,403 records dated 2026 and Scopus 5,409, all outside the review period.
- **Scopus abstracts.** OpenAlex and Crossref had no abstract for 34 of the 100 sampled Scopus records; the Scopus Abstract Retrieval API supplied all 34.

## Changes after the first run

- **Reuse fallback.** The fallback rule now also covers a Practice value whose development set sources all carry the other value too. *Reuse* takes "data reuse" and "data re-use" from the Candidate terms table, the two terms the plan names, as one fallback term per database in `terms.csv` and `term_syntax.csv`. A fallback term enters the query without the yield test.
- **Date limit ends at 2025.** The load and the term runs' load column now cover 2015 to 2025 (`load_2015_2025`). Citation searching of the included sources catches 2025 work that databases date by a 2026 issue.
- **Scopus precision abstracts.** The precision block now asks the Scopus Abstract Retrieval API for any Scopus record OpenAlex and Crossref lack.
- **Rerun needed.** The PubMed and Scopus query and precision blocks run again with these changes, then Web of Science once its key arrives.

## Reference set reconstruction, 16 November 2026

- **No published list.** Chawinga and Zinn (2019) analyse 105 sources but publish no list of them. The Crossref record holds the paper's 124 references and no supplementary material. The first author's PhD thesis (University of the Western Cape, 2019) has no list in its chapters, tables or appendices, and cites the review once. His only data deposit holds his PhD survey data. OpenAlex lists no dataset among his 41 works, DataCite has none, and the profiles reachable (ResearchGate, Academia.edu) hold only the paper. ORCID, Zenodo and Google Scholar blocked automated access.
- **Source of the reconstruction.** Elsevier's Article Retrieval API returns the paper's full text as XML, with every citation linked to its reference and placed in its section or table. Table 2 names its sources as plain text, without links, so they are matched by first author and year, allowing a year either way only where the reference list has no reference by that author with Table 2's year. That catches Burgi et al., whom Table 2 dates 2016 and the reference list 2017, without taking Rowhani-Farid and Barnett (2016) for Rowhani-Farid et al. (2017).
- **Rules.** A reference is in the reference set if Table 2 names it, if section 4 or 5 cites it, or if it supplies a country section 4.3 lists among countries with a single included publication. The third rule adds Chigwada (2017) for Zimbabwe and Ng'eno (2018) for Kenya, both cited only in sections 1 and 2.
- **Result: 102 of 105.** Table 2 and sections 4 and 5 give 100; section 4.3 gives 2 more.
- **Checks against the paper's counts.** Block 11 prints them; for the reference set of 102:
  - *Journal articles:* 82, against the paper's 83, so one missing source is a journal article. The count also shows the paper counted Gupta (2013), Steen (2011) and Higgins (2011), which the earlier selection left out as background: without them the set would be four articles short, and only three journal articles remain outside it.
  - *Theses:* 11, against the paper's 10. All 11 are theses: the reference entries of He (2016), Scott (2014) and Zvyagintseva (2015) say so, and repository records confirm He's doctoral dissertation (University of Maryland) and Zvyagintseva's master's thesis (University of Alberta). The extra one is likely Ng'eno (2018), the only thesis the section 4.3 rule adds: without it the set holds 10 theses and 9 sources from 2018, matching both the paper's count and Fig. 4. Section 4.3 still names Kenya, and Ng'eno's is the only title naming Kenya, though a Kenyan study whose title does not name Kenya could account for it. Ng'eno stays in, so that every rule applies to every reference without exceptions made after seeing the result.
  - *Books, reports and other items:* 9 (2 reports, 3 books, 1 book chapter, 3 other), against the paper's 12 (8 reports, 4 books). The paper's split depends on how it classed grey items such as Mundel (2014), Guedon (2015), the European Commission (2012) and Ostell (2009), so it can't be checked item by item.
  - *Years:* the reference set does not match Fig. 4 year by year (2007: 4 against 3; 2008: 4 against 3; 2010: 4 against 6; 2012: 10 against 14; 2014: 4 against 6; 2017: 10 against 12). Fig. 4 dates sources differently from the reference list or miscounts, so it can't identify the missing sources.
- **The missing three.** References cited only in sections 1, 2, 6 or 7 and dated 2007 to 2018, besides the two section 4.3 supplies: Corti et al. (2014), Housewright et al. (2013), Kambatla et al. (2014), Pryor (2012), Rowhani-Farid and Barnett (2016), the Royal Society (2012) and Wicherts and Bakker (2012). By the counts, one is a journal article (Kambatla, Rowhani-Farid and Barnett, or Wicherts and Bakker) and two are books or reports (two of Corti, Housewright, Pryor and the Royal Society). Nothing in the paper decides which.
- **Change from the earlier set.** The earlier reference set held 97 references selected by reading each citation. The reconstruction holds all 97 and adds Gupta, Steen, Higgins, Chigwada and Ng'eno. All files built on the earlier set are rebuilt from `reference_candidates.csv`.

## Folder layout, 16 November 2026

- **Search development folder.** The plan, notebook 00, the log and the summary of outcomes moved into `analysis/00_search-development/`. The plan became its `index.qmd`, and the site shows it as the Search development section under Analysis.
- **Data split.** The files in `data/search_tests/` moved by who produces them. Files from the APIs, the local model and the precision screening went to `data/raw/search-development/`. Files notebook 00 builds went to `data/processed/search-development/`: `reference_sources.csv`, `counts.csv`, `verdict.csv`, `statement_matches.csv`, `terms.csv` and `term_syntax.csv`. Until notebook 00 is rebuilt, those six files are still the ones I built by hand, and `reference_codes.csv` holds my codes, not the local model's.
- **Scripts.** The Markdown file of paste-ready blocks, renamed from `step3_blocks.md` to `server_blocks.md` earlier the same day, became one Python script per block in `retrieval/`. `query.py` and `precision.py` take the database as `pubmed`, `scopus` or `web-of-science`, which replaces three copies of each block. The plan's Runs section gives the commands.
- **Prompts.** The coding and indexing prompts moved to `prompts/`. The launch script stays in `scripts/` at the repo root, so other work can use it.
- **Query writes into a processed file.** `query.py` still fills the step 3 columns of `terms.csv`. The plan has it write `term_results.csv` in raw; that change comes with the step 3 rerun.
- **Notebook 00 stops at its fourth cell.** Its code reads a `key` column that `reference_candidates.csv` lost when the reference set was rebuilt. This predates the move and gets fixed in the notebook 00 rebuild.

## Local model server, 16 November 2026

- **llama.cpp in place of Ollama.** `scripts/launch_rds_llm.sh` now runs llama.cpp's server. Ollama serves models from its own registry, which keeps only the file a tag points to now, so a recorded digest can show a model changed but can't bring the old one back. The model is now a GGUF file on Hugging Face, fixed by repository, revision and SHA-256, and Hugging Face keeps every revision.
- **Models.** `qwen3.5-122b` is unsloth's Q4_K_M build of Qwen3.5-122B-A10B, revision `51eab4d59d53f573fb9206cb3ce613f1d0aa392b`, three files totalling 76.5 GB, for GPUs 5 to 8. `qwen3.8-27b` is unsloth's UD-Q4_K_M build of Qwen3.8-27B, revision `4af51b3542f775b0a8e4b310bfb3f17e01c306c9`, 16.6 GB, for one GPU. The checksums are in the script.
- **Server.** The llama.cpp image is pinned to build b12375, the newest CUDA 12 server image on 16 November. Build b12380, the newest release, has no CUDA 12 image, and the CUDA 13 images need a 580-series NVIDIA driver; the GPU server has 565.57, which supports CUDA up to 12.7. The server runs one request at a time, loads the model fully into memory, and uses each model's own chat template. Temperature, seed and thinking are set per request by the scripts that call it.

## Model choice, 16 November 2026

- **Runs.** `coding.py` coded the 102 references twice, with Qwen3.5-122B-A10B on GPUs 5 to 8 and Qwen3.8-27B on GPU 9, with the same prompt, schema and settings: 881 and 771 codes, 19 references coded on title alone in each.
- **First 122b run stopped.** Before the schema, the model gave values off the list ("ownership", "funding") and theme names as values, and the passage check rejected passages from OpenAlex abstracts with split words ("infor mation") and a lost first letter. The answer is now held to a JSON schema of the prompt's values, and the check compares letters and digits and accepts a passage with at least 95% of its characters matching in order at one place. The run restarted from the first reference.
- **Problems.** The 122b has 4 codes with a problem: 3 passages starting with a copied "Title:" label (Wiley 2018, Volk 2014, Yoon 2017), and 1 passage joining the start of a sentence in Mbuagbaw 2017 to item (4) of its list. The 27b has 10, mostly terms not in the title or abstract.
- **The two models against each other**, over 102 sources, as agreement and Cohen's kappa: Practice 0.86 and 0.74; `data_origin` 0.94 and 0.80; `field` 0.86 and 0.78; `source_type` 0.79 and 0.71; language 1.00. Factor themes, whether a source reports any factor under each: factors that obstruct 0.88 and 0.77; factors that facilitate 0.84 and 0.68; stakeholder perspectives 0.93 and 0.63; policies and what drive them 0.92 and 0.84; mechanisms for implementation 0.84 and 0.68. The 122b codes 9 sources *both* that the 27b codes *sharing*, and 3.0 factors per source against 2.3.
- **Each model against my hand codes**, over the 70 sources both sets hold, kappa for the 122b then the 27b: Practice 0.57 and 0.50; `data_origin` 0.46 and 0.58; `field` 0.76 and 0.85; `source_type` 0.53 and 0.67; factor themes 0.46 to 0.61 and 0.59 to 0.69. I coded 37 sources from their titles alone, so these figures measure distance from my codes, not accuracy.
- **Choice.** The 122b, because its terms and passages come from the sources word for word, and recorded terms become search terms in step 2. The 27b's codes stay, so anyone with one 24 GB GPU can rerun the coding and see how far the smaller model departs.
- **File names.** Each file of codes keeps the name of the model that made it. `CODES` in `retrieval/search_lib.py` and the file list in notebook 00 name `reference_codes_qwen3.5-122b.csv` as the codes of record. My hand codes, `reference_codes.csv`, were deleted; they stay in the repository's history. `query.py` and notebook 00 still read the hand codes' columns (`key`, `Practice`), so both need reworking for the new columns before they run again.

## Indexing assignments, 16 November 2026

- **Runs.** `indexing.py` sent each of the 637 distinct terms in `reference_indexing.csv` to Qwen3.5-122B-A10B and to Qwen3.8-27B, one term at a time, with the coding settings and the answer held to the prompt's values. Neither run had a reply problem. The 122b placed 226 terms under a PCC part: 34 *sharing*, 5 *reuse*, 187 a factor. The 27b placed 191.
- **The two models against each other**, as agreement and Cohen's kappa: same value 0.85 and 0.73; same PCC part or *none* 0.90 and 0.81; placed against *none* 0.92 and 0.81. All 5 of the 122b's *reuse* terms are *reuse* for the 27b, which adds "replication". The 27b agrees on 29 of the 122b's 34 *sharing* terms; it leaves out MeSH Information Dissemination, "data sharing culture", "data sharing framework", "data transparency" and "open data publishing", and adds "data accessibility". On factors, the 122b mostly places terms the 27b leaves as *none*: 22 under factors that facilitate, 9 under mechanisms for implementation, 5 each under factors that obstruct and policies and what drive them.
- **Doubtful assignments in the 122b's run**, kept as they are so the run stays reproducible:
  - *Sharing:* "data access", "data availability", "research data access", "remote data access" and "raw data access" could as well name reuse. Step 3's yield test decides whether any enters a query.
  - *Reuse:* MeSH "Access to Information", from a scope note on the right to obtain and use information others collected; broad, and also left to step 3.
  - *Wrong theme:* the keyword "stakeholder perspectives" became *stewardship*, under mechanisms for implementation, in both runs; "stakeholder engagement" went there too.
  - *Inconsistent:* "trust" is *perceptions* as an OpenAlex keyword and *willingness* as an author keyword and as MeSH; both sit under stakeholder perspectives.
  - *Loose factor placements:* library terms ("librarian roles", "library services", "single point of contact") as *infrastructure*; problems in the data ("data heterogeneity", "data scarcity") as *barriers*; "data ownership" and "research transparency" as *policies*. Factor terms go to screening only.
- **Choice.** The 122b's assignments, `term_assignments_qwen3.5-122b.csv`, for the same reason as its codes, and because it places MeSH Information Dissemination under *sharing*.

## Notebook 00, step 1 files, 16 November 2026

- **Built by the notebook.** Notebook 00 now builds `reference_sources.csv`, `counts.csv`, `verdict.csv` and `statement_matches.csv` from `reference_candidates.csv`, `reference_lookups.csv` and `reference_codes_qwen3.5-122b.csv`, and writes them to `data/processed/search-development/`. These replace the files I built by hand.
- **Set.** Development set: 2007 to 2014, 60 sources. Test set: 2015 or later, 42 sources. Wiley 2018 is dated 25 September 2018 by Crossref, after the paper's search ended in July 2018; the paper cites it, so it stays in the test set.
- **Eligibility.** 80 sources are eligible apart from year (46 development, 34 test), and 34 are in scope, all in the test set. Reasons: *date* 46, *not-data-sharing* 13, *not-factors* 6, *not-research-data* 3. The plan's In scope criteria have no `tier` condition, so the codebook's *tier2-not-review* code is not applied here.
- **Verdict.** All seven PCC parts are *covered*: sharing 45 development and 31 test sources; reuse 17 and 9; factors that obstruct 30 and 19; factors that facilitate 36 and 26; stakeholder perspectives 6 and 4; policies and what drive them 27 and 19; mechanisms for implementation 18 and 13.
- **Search statements**, against titles and abstracts: "research data sharing AND researchers" reaches 2 sources as phrases and 29 as separate words; "digital curation AND data sharing" none; "research data sharing AND open science" 1 and 8; "research data sharing AND open data" 0 and 17.
- **Comparison.** `comparison.csv` lost its evidence column, whose counts came from my hand codes. It keeps the criteria and the relation, the recorded judgment; notebook 00 adds the current counts beside each criterion.

## Notebook 00, step 2 files, 16 November 2026

- **Built by the notebook.** Notebook 00 now builds `terms.csv` and `term_syntax.csv` from `reference_codes_qwen3.5-122b.csv`, `reference_indexing.csv` and `term_assignments_qwen3.5-122b.csv`, for the 60 development set sources, replacing the files I built by hand. `term_syntax.csv` holds 994 written forms; `terms.csv` holds 526 rows over the three databases.
- **Candidates for step 3**, per database: 51 *sharing* and 21 *reuse* terms in PubMed, 50 and 20 in Scopus and Web of Science. The strongest: OpenAlex keyword "data sharing" (26 sources), MeSH Information Dissemination (15), recorded "data sharing" (14), and for *reuse*, OpenAlex keyword "data reuse" (8) and MeSH Access to Information (6).
- **No fallback.** Every Practice value has development set sources of its own (*reuse*: 1 coded *reuse* alone, 16 coded *both*), so no fallback terms come from the Candidate terms table.
- **Recorded terms from *both*.** A source coded *both* gives its one recorded term to *sharing* and *reuse*, so the *reuse* list carries sharing words such as "share their data". Step 3 tests *sharing* and *reuse* terms together, so this changes no query.
- **Weak recorded terms.** The model recorded some terms that are not search terms, such as "use", "mine these data" and "re use, preservation and, particularly, data sharing". Step 3's yield rule decides on them.
- **Truncation.** Single words truncate at their stem, so "challenges" becomes challeng\* and "databases" databas\*.
- **Step 3 results stale.** `query_tests.csv`, `query_misses.csv` and the load and precision files still come from the first step 3 run, on the hand-built terms. `query.py` and `precision.py` need reworking for the new columns and `term_results.csv` before step 3 reruns.

## Tier in In scope, 16 November 2026

- **In scope** now applies the screening guide's tier criterion: a source in another field is in scope only as a review (`source_type` *review*). 10 sources are in scope, down from 34. Reasons, first code per source in the codebook's order: *tier2-not-review* 50, *date* 20, *not-data-sharing* 13, *not-factors* 6, *not-research-data* 3.
- **Eligible apart from year** leaves out `tier` as well as Year, because the query carries no field terms and the `tier` decision happens at screening. It is unchanged: 46 development and 34 test sources, so the verdict and the terms are unchanged.

## Step 3 scripts for the new files, 16 November 2026

- **`query.py`** reads sources by `ref_id`, takes the *sharing* and *reuse* terms from the rebuilt `terms.csv`, and writes its results for each term to `term_results.csv`, replacing that database's rows, in place of filling columns in `terms.csv`. `query_misses.csv` lists each source's recorded Practice terms from the codes of record.
- **Coverage** adds the test set sources eligible apart from year, beside the whole test set and the In scope sources. With the tier criterion, only 10 sources are in scope, so the eligible sources (34) give the steadier measure, and they match the sources the yield rule uses in the development set.
- **Shared files.** The writer for files the three databases share now keeps every column any row has, so rows from the first step 3 run don't block the new columns.
- **Checked** against stand-in database responses for Scopus and PubMed: the term runs, threshold, draft, trim, coverage, load and all four output files.

## Step 3 rerun stopped and fixed, 16 November 2026

- **PubMed load.** PubMed's esearch returns at most 9,999 PMIDs for one search, and the new PubMed query returned more for 2015 to 2025, so its load crashed. `search_lib.py` now fetches a result that size one publication year at a time, and a year still too large one month at a time.
- **Long queries with identifiers.** Scopus answered "400 Bad Request" to the threshold request, which joined all its candidates with 25 DOIs; the same candidates without DOIs, 2,118 characters, went through. `query.py` now takes the sources any OR of terms retrieves as the union of the sources each term retrieves in its own term run, so every request with identifiers carries one term. Record counts and the load still use the joined query, which has no identifiers. Test set coverage is the union of each final term's run against the test set.
- **Terms that name no data.** The model recorded terms such as "use", "share", "sharing" and "reuse". "use" alone returns 6,969,665 Web of Science records for 2007 to 2014, which brought the threshold down to 0.004 sources per 1,000 records, so the yield rule would have let almost any term in. A *sharing* or *reuse* term now goes to step 3 only if it contains *data* or is a MeSH heading, since the Concept is the sharing and reuse of research data. Candidates per database: 37 *sharing* and 12 *reuse* in PubMed, 36 and 11 in Scopus and Web of Science. "secondary analysis" names reuse without the word and drops out with the rest.
- **Stale precision samples.** Each crashed query run left the loop to run `precision.py` on the first run's load file. The samples it drew were identical to the committed ones, so nothing changed; the rerun redraws them from the new loads.

## Step 3 rerun outcomes and the reuse terms, 16 November 2026

- **Queries from the rerun** (commit "Rerun step 3 in PubMed, Scopus and Web of Science on the rebuilt terms"): PubMed `"data sharing"[tiab] OR "shared data"[tiab]`, load 8,425; Scopus `"data sharing"` with "make the data and code available" and "make data available", load 30,755; Web of Science the same three terms, load 19,842. Coverage of the test set sources eligible apart from year: 0.83, 0.83 and 0.74. No query kept a *reuse* term.
- **Reuse.** "data reuse" came closest: yield 1.531 against Scopus's threshold of 1.598, and 2.169 against Web of Science's 2.623, with loads of 2,544 and 2,000. 16 of the 17 development set sources coded for *reuse* are also coded *both*, so "data sharing" already reaches them and a reuse term gets credit only for what nothing else reaches; the test set holds sharing sources and can't test reuse either. *Reuse* now always takes its Candidate terms, "data reuse" and "data re-use", which enter each query without the yield test.
- **Test set seen before the reuse change.** I read the test set misses in `query_misses.csv` before proposing the reuse terms. The reason for the change came from the development set (16 of 17 reuse sources also coded *both*), and the reuse terms changed no test coverage figure, since the test set holds sharing sources; but the test set was not untouched when the final queries were set.
- **Misses accepted.** The eligible test set sources the queries miss use wording a phrase search can't predict: Watson 2015 ("making the results of that research available to everyone"), Specht et al. 2015 (data management challenges; "publish, access and re-use"), Chen and Wu 2017 ("research data management and sharing", which splits the phrase), and Wittenberg and Elings 2017 and Chiware and Mathe 2016 (research data management programmes). Catching them would take terms such as "data management", with loads in the tens of thousands. They stay missed and recorded.
- **Two recorded phrases** in the Scopus and Web of Science queries, "make the data and code available" and "make data available", each reach the one development source whose abstract they come from, for almost no records. They pass the yield rule as it stands, add almost nothing to the load, and won't generalise.

## Final queries and the precision screening page, 16 November 2026

- **Final queries** (commit "Rerun step 3 with the reuse terms: final queries for PubMed, Scopus and Web of Science"):
  - *PubMed:* `"data sharing"[tiab] OR "shared data"[tiab] OR "data re-use"[tiab] OR "data reuse"[tiab]`, load 8,824; test coverage 0.85 overall, 0.83 eligible apart from year (0.55 to 0.95), 1.0 in scope.
  - *Scopus:* `TITLE-ABS-KEY("data sharing")`, "make the data and code available", "make data available" and "data re-use" OR "data reuse", load 33,089; coverage 0.76 overall, 0.83 eligible (0.64 to 0.93), 1.0 in scope.
  - *Web of Science:* the same terms in `TS`, load 21,721; coverage 0.67 overall, 0.74 eligible (0.51 to 0.88), 0.89 in scope.
  The reuse terms add 399 records in PubMed, 2,334 in Scopus and 1,879 in Web of Science.
- **Web of Science abstracts.** `precision.py` now tries PubMed and then the Scopus Abstract Retrieval API by DOI for Web of Science records; the sample's records without an abstract fell from 25 to 5. PubMed's sample lacks 3, Scopus's none.
- **Screening page.** Notebook 00 builds `precision_screening.html` in `data/processed/search-development/` from the three samples, the template `precision_screening_template.html` and the exclusion codes in `codebook.yml`. Decisions save in the browser; Export CSV writes each database's sample with the decisions, for `data/raw/search-development/`.

## The final queries are too large, 18 November 2026

- **Problem.** The final queries return 8,824 records in PubMed, 33,089 in Scopus and 21,721 in Web of Science for 2015 to 2025. That is far more than can be screened. The method picks terms by yield and checks coverage, but nothing in it limits the total load, and I did not check its output against that goal. Scopus's first run, at 32,994, already showed it.
- **The candidates came only from the reference set's wording.** Step 3 chose among the terms the model recorded from the development sources' titles and abstracts and their indexing terms. Common ways of saying data sharing that those sources did not use, such as "sharing of data", "share\* data", "data deposit\*", "data repositor\*" and "secondary use", were never tested. Zack's Candidate terms table entered only as the reuse fallback, "data reuse" and "data re-use".
- **Queries Q1 to Q4** on the search strategy page are obsolete and are not the base for the new queries.
- **Where the queries stand.** All three come down to "data sharing" plus the reuse terms. Adding factor terms, as the review's question asks, gives Zack's original PCC structure: sharing and reuse terms AND factor terms. What the work adds is evidence for each term: how many reference set studies it finds and how many records it costs.
- **Precision screening is not needed to choose the queries.** The split into development (2007 to 2014) and test (2015 on) sets measures coverage, whether a query finds studies it was not built from; precision is a separate figure, how much of the load is relevant. The queries are chosen on coverage and load.
- **Numbers behind the measures.** The reference set holds 102 studies: 60 in the development set and 42 in the test set. 46 development studies are eligible apart from year, and about 40 of those have a DOI or PMID a database can be asked about. The test set studies are held back to check the finished queries.
- **The score.** New studies found divided by extra records added. Adding, at each step, the term with the highest score keeps each step close to the most studies available for that many records, so the query can stop at the step whose load is screenable.
- **Next approach.** For each database, a table of every plausible candidate term with its record count for 2015 to 2025 and the development studies it finds: about 15 to 20 sharing and reuse terms, from step 3's candidates and standard synonyms, and about 35 factor terms, from the Candidate terms table and general words for a factor such as factor\*, influenc\* and determinant\*. Zack picks the terms from the table. Each choice is measured anywhere in the title or abstract, with the sharing terms in the title only, and with the factor term within 5 words of the sharing term (Scopus and Web of Science only), all limited to English or French, as the screening guide's Criteria require. The test set then gives the chosen queries' coverage.
- **Drawbacks of selecting terms this way:**
  - About 40 development studies decide, so one or two studies can make or break a term.
  - A phrase taken from one study finds that study for almost no records and scores well, but finds no others.
  - Chawinga and Zinn found the reference set with their own search, built around "research data sharing", so terms resembling it are favoured.
  - The development studies date from 2007 to 2014, so later wording, such as FAIR, has no studies to earn its place.
  - Reuse alone, and anything else the reference set lacks, cannot be tested.
  - Adding one term at a time makes the result depend on the order, and may miss the best combination.
  - Load counts every record, relevant or not.
  - The candidate lists are a judgment; a term never offered cannot be chosen.
  - About 29 test studies can be checked, so coverage carries intervals of roughly 15 to 20 points either way.
- **Reuse.** Whether "data reuse" and "data re-use" belong is open; the reference set cannot test it.

## Term evidence: one title block, 18 November 2026

Runs 1 to 14 in the Term evidence section of notebook 00 hold the code, the files and what each run settled. The decisions:

- **Sharing block (run 1).** "data sharing", with "shar\* data" added in PubMed, where it finds Bertzky and Stoll-Kleemann 2009, Cooper 2007 and Rohlfing and Poline 2012. "data publication", "data access" and "data availability" each add only Costello 2009 and stay out.
- **A small factor block looks picked (runs 2 and 3).** Choosing a few factor terms by yield gave blocks of about six terms. Zack judged that a reader would ask why those terms and no others. Runs 5 to 9 used the whole Candidate terms table in their place, with six general words for a factor that Claude proposed: factor\*, influenc\*, determinant\*, driver\*, concern\* and trust.
- **Five terms that find no development study go (run 5).** facilitator\*, driver\*, interoperab\*, "open research" and "digital curation". A query drops out when another finds at least as many development studies in fewer records; in every database the block with these five terms dropped out against the block without them.
- **privacy goes (run 6).** Removing privacy loses no development study in any database. Zack first judged data protection outside the factors the PCC table asks about; the coding prompt and the screening guide keep privacy as a factor that obstructs sharing, so screening still applies it.
- **Cutting factor terms cannot bring the load down far (run 7).** Studies drop out within two or three cuts in Scopus and Web of Science, and with one factor term left the queries still return 2,209, 5,632 and 9,051 records. The cut order, set by cost, also removes polic\* and barrier\* early, which a reader would not accept in a query about factors.
- **A form of share within 5 words of data, in the title, replaces the phrase (runs 10 and 11).** The phrase misses titles such as "sharing research data" (Borgman 2012), "sharing of health data" (Haddow et al. 2011) and "sharing and reuse of ecological data" (Zimmerman 2008). With duplicates removed:

  | Query | Records | Development studies found |
  |---|--:|--:|
  | "data sharing" in the title OR with a factor term within 5 words (runs 8 and 9) | 14,255 | 28 of 35 |
  | share within 3 words of data, title | 9,591 | 28 of 35 |
  | share within 5 words of data, title | 10,493 | 29 of 35 |
  | share within 5 words of data, title, OR "data sharing" with a factor term | 18,135 | 31 of 35 |

  The factor terms add Fisher and Fortmann 2010 and Piwowar 2011 for 7,642 records, so they leave the query and guide screening, as step 2 first proposed.
- **Abstracts stay out.** A form of share within 5 words of data in title and abstract returns about 8 times the records for 1 to 3 more development studies per database. Zack rejected the ways of recovering abstract-only studies: author keywords and MeSH major topics, factor terms within 2 or 3 words of "data sharing" in the abstract, and title terms such as "open data" and "research data management". Citation searching is the backstop.
- **Reuse leaves the query.** Zack's decision: the review asks about sharing.
- **Development misses are no manual additions.** Cohn 2012, Costello 2009, McCullough 2009 and Parr 2007 stay missed by every query tested; their titles say nothing of sharing data. All development studies date from 2007 to 2014, outside the review's years, so manual additions can only come from the test set's misses. This replaces the one-offs entry drafted earlier in the day, which was never applied.
- **Web of Science's language limit.** Its API rejects `LA=(English OR French)` beside `shar* NEAR/n data`, with an error saying it cannot search `LA` at all. The limit works elsewhere: an invented language returns no records, and English or French removes about 0.5%. Web of Science counts for share-near-data queries carry the date limit alone; the review's exports come from the Web of Science site, where the limit works.
- **No document type limit (run 12).** Editorials, letters, notes and news make up 8 to 18% of the records. Most opinion pieces are indexed as Article or Review, and a Note or Editorial can be a policy document (Harding et al. 2013) or an empirical study (Huang et al. 2013), so a limit would keep most opinion pieces and drop sources the review keeps. The protocol makes all source types eligible; a limit would change that. Zack has not decided.
- **Data sharing in the computing sense (runs 13 to 15).** Titles with technical words such as blockchain\*, cloud and encrypt\* make up 6% of the records in PubMed, 35% in Scopus and 29% in Web of Science, and include no development study. A NOT clause on 13 such words cut the records to 7,505 but removed titles on incentives, consent and governance in health data sharing; the development set, from before 2015, cannot speak to these words.
- **Eligibility gains a line.** Zack's principle: sources that design, build or evaluate a specific system, product or service for sharing data are out of scope. The NOT clause removes titles that almost always mark such a source: blockchain\*, "smart contract\*", IoT, "internet of things", vehicular, "edge computing" and cloud. Records without duplicates fall from 10,493 to 7,933, with all 29 development studies kept. attribute-based and cryptograph\* would save 76 more and stay out, by Zack's agreement. encrypt\*, "access control", "privacy-preserving", scheme and secure also mark methods and governance of research data, and "federated learning" an alternative to sharing health research data that the review may cover, so screening handles them. A study of why people use such a system concerns factors and is in scope; the clause removes it, and citation searching is the backstop.
- **The query.** Title: share\* within 5 words of data, NOT title: blockchain\* OR "smart contract\*" OR IoT OR "internet of things" OR vehicular OR "edge computing" OR cloud; 2015 to 2025; English or French. The notebook gives each database's syntax.
- **Test set (run 16).** The query finds 8 of 12 indexed test studies in PubMed, 16 of 24 in Scopus, 12 of 19 in Web of Science, 18 of 26 in the three together (0.69, 95% interval 0.50 to 0.84), and 9 of the 10 coded in scope. The test set's misses had been read on 16 November, in step 3, before this query existed; the query was not built from them.
- **Test studies the query misses.** No query can find 8: Bishoff and Johnston 2015 and He 2016, both with data sharing in the title, and Zvyagintseva 2015 are in none of the databases; Brown et al. 2015, Curty 2015, Guédon 2015, Koopman 2015 and Yoon 2015 have no DOI or PMID. The query misses 8 that a database holds, all coded out of scope but one:
  - **Chiware and Mathe 2016**, "Academic libraries' role in research data management services: A south African perspective", DOI 10.7553/81-2-1563; health, empirical, in scope; in Web of Science only. **Added to the search results by hand.**
  - Chigwada et al. 2017, "Research data management in research institutions in Zimbabwe", DOI 10.5334/dsj-2017-031; in Scopus.
  - Schöpfel et al. 2018, "Research data management in the French National Research Center (CNRS)", DOI 10.1108/dta-01-2017-0005; in Scopus and Web of Science.
  - Wittenberg and Elings 2017, "Building a research data management service at the University of California, Berkeley: A tale of collaboration", DOI 10.1177/0340035216686982; in Scopus and Web of Science.
  - Specht et al. 2015, "Data management challenges in analysis and synthesis in the ecosystem sciences", DOI 10.1016/j.scitotenv.2015.03.092, PMID 25891686; in all three.
  - Schmidt et al. 2016, "Open data in global environmental research: The Belmont Forum's open data survey", DOI 10.1371/journal.pone.0146695, PMID 26771577; in all three.
  - Watson 2015, "When will 'open science' become simply 'science'?", DOI 10.1186/s13059-015-0669-2, PMID 25986601; in all three.
  - Curty et al. 2017, "Attitudes and norms affecting scientists' data reuse", DOI 10.1371/journal.pone.0189288, PMID 29281658; in all three.

  Titles naming research data management or open data would add mostly sources out of scope, and open data titles include a literature on open government data, so neither enters the query.
- **Stopping rule.** Open. With 100 to 200 included sources, Callaghan and Müller-Hansen's criterion would stop after about a third to a half of the records, by Claude's simulation, which assumes ASReview ranks well. Rules that stop after a run of irrelevant records screen less but make no recall claim, and the evaluations the protocol cites find no run length that holds across datasets.
- **Known-item test (run 17).** The query finds 8 of the 11 health research items and all 5 cross-disciplinary reviews on the search strategy page's known-item list, and all 5 adjacent and comparator items. It misses three items the databases hold: Hutchings et al. 2020 ("…the secondary use and sharing of health administrative and clinical trial data", DOI 10.1186/s13643-020-01485-5), where seven words separate sharing from data; Swales et al. 2024 ("The anatomy of a data transfer agreement for health research", DOI 10.3389/fphar.2024.1332700); and Inau et al. 2023 ("…data principles in health data stewardship: scoping review", DOI 10.2196/45013). Swales and Inau concern governance mechanisms whose titles do not name sharing.
- **Governance terms stay out (run 18).** Title terms against the query's 7,933 records, duplicates removed: "data access" +1,077, "data transfer" +1,617 (finds Swales), "data governance" +1,120, "data stewardship" +82 (finds Inau), the FAIR phrases +425; 4,304 together. Zack's decision: the query stays one idea, a title that names sharing data, since a term added to catch one known source looks picked. This run drew on the known-item list, so that list no longer tests these terms independently.
- **Added by hand.** Chiware and Mathe 2016, Hutchings et al. 2020, Swales et al. 2024 and Inau et al. 2023, reported as identified from other sources.
- **Citation searching dropped.** Zack's decision: the review does no citation searching. The entries above that name it as a backstop no longer hold; the protocol says nothing of it.
- **Privacy.** The coding prompt and the screening guide list privacy as a factor that obstructs sharing, so screening applies it; dropping it from the factor block in run 6 cost no known source.
- **bib-dedupe.** The protocol deduplicates with bib-dedupe. Claude named ASySD in the notebook text and in the chat on 18 November; the notebook now says bib-dedupe.
- **Reuse-only sources leave the known sources.** Notebook 00's eligibility rule now gives `not-data-sharing` to sources coded *reuse* as well as *neither*, since the review asks about sharing. Four sources change: Higgins 2011 (development, in none of the databases) and Curty et al. 2017, Yoon 2015 and Curty 2015 (test). Eligible apart from year falls from 46 to 45 development and 34 to 31 test sources. No development figure changes. Test coverage becomes 8 of 11 in PubMed, 16 of 23 in Scopus, 12 of 18 in Web of Science and 18 of 25 together (0.72, 95% interval 0.52 to 0.86); 9 of 10 in scope. Runs 1 to 15 and 17 to 18 ran under the old rule; only run 16 uses the test set and is rerun under the new one.

## Seed sample and stopping rule, 18 November 2026

- **Seed sample.** 200 records drawn at random, with a fixed random seed, from the deduplicated records, replacing the Q1 seed. Callaghan and Müller-Hansen (2020) began their evaluation with a random sample of 200, so the seed matches the conditions the stopping criterion was tested under. At a 2% share of relevant records, 200 records leave about a 2% chance of a seed with no relevant record, against 20% for 80 records (1%, SAFE's example); the share in the seed estimates the share across all records, with a 95% interval a few points wide. A 2024 simulation abstract with ASReview found larger initial random samples raise total screening.
- **Stopping rule.** Callaghan and Müller-Hansen's criterion stays, in its ranked form, which reuses the ranked screening decisions and needs no extra random sampling: in their evaluation it saved 17% of screening on average and missed the 95% recall target in 0.95% of runs, against 15% and 3.29% for the random sampling form. The test runs on the exported decisions after each session, with buscarpy, in `02-screening`. The protocol now states that screening may cover most of the records.
- **Alternatives read.** ASReview LAB offers only a threshold of irrelevant records since the last relevant one, unset by default. SAFE (Boetje and van de Schoot 2024) combines a random 1% set, a minimum of 10% screened, twice the estimated relevant records, 50 irrelevant records in a row, a second model and a quality check; its thresholds are expert opinion and the paper presents no evaluation.

## To do

- **Artificial intelligence section of `research-protocol.qmd`.** The sentence "The query terms come from those codes." oversimplifies how the terms were selected. Rewrite it once the query is settled, so it states how the terms were chosen: from measured records and development studies in the three databases, as the Term evidence section records.
- **Search strategy in `research-protocol.qmd`.** The single title block, the reasons the factor terms, abstracts and reuse are left out, and the NOT clause.
- **Eligibility in `research-protocol.qmd` and the screening guide.** The line on sources that design, build or evaluate a specific system, product or service for sharing data.
- **Sources added by hand.** Chiware and Mathe 2016, Hutchings et al. 2020, Swales et al. 2024 and Inau et al. 2023 go into the search results by hand, reported as identified from other sources.
- **Statistical review.** A statistician reviews the seed sample size and the stopping rule's application before screening begins.
- **Screening guide.** The Candidate terms table and the factor themes, as guidance for judging whether a record reports factors, and data sharing in the computing sense as an exclusion.
- **Step 3 of notebook 00** still shows the queries built by the yield rule; the test set check of the chosen query replaces it.
