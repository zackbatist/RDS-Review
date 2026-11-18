# Search development outcomes

Outcomes of the plan in `index.qmd`, as of 18 November 2026. `log.md` records every judgment behind these figures, and notebook 00 shows them.

## Step 1. Comparability assessment

**Reference set.** 102 references Chawinga and Zinn (2019) cite as findings: 60 in the development set (2007 to 2014) and 42 in the test set (2015 on).

**Eligibility.** A local model, Qwen3.5-122B-A10B, coded each reference from its title and abstract; notebook 00 applies the eligibility criteria to the codes. 45 development and 31 test sources are eligible apart from year, and 39 and 28 of them have a DOI or PMID. Sources about reuse alone fall outside the review's question. 10 test sources are in scope. Qwen3.8-27B coded the same references for comparison; the two agree on 79% to 100% of the codes for each variable.

**Verdict.** `verdict.csv` marks all seven PCC parts *covered* in both sets. *Stakeholder perspectives* rests on 6 development and 4 test sources.

**Chawinga and Zinn's search statements** reach a minority of the sources they included, and offer no template for the RDS-Review query.

## Step 2. Terms by PCC part

`terms.csv` lists the terms the development set sources use for each PCC part. Its sharing and reuse terms fed the first version of step 3, which was replaced; its factor terms informed the screening guide.

## Step 3. Query and testing

**Query.** A form of *share* within five words of *data* in the title, leaving out titles that name blockchain, smart contracts, the Internet of Things, vehicular networks, edge computing or cloud computing, for 2015 to 2025 in English and French. The search strategy page gives each database's string.

**Load.** 2,437 records in PubMed, 7,067 in Scopus and 6,149 in Web of Science on 18 November 2026; 7,933 once matched on DOI, or on title and year.

**Development set.** The query retrieves 29 of the 35 eligible development sources that at least one database indexes. The phrase "data sharing" in titles retrieves 16 or 17 in each database, against 20 to 28 for the query. Searching abstracts as well returns about eight times the records for at most three more sources. Factor terms add two sources for about 7,600 records, so they stay out of the query.

**Test set.** 18 of the 25 eligible test sources that at least one database indexes (0.72, 95% interval 0.52 to 0.86), and 9 of the 10 in scope. The 7 indexed sources it misses name research data management, open data or open science in their titles; all but Chiware and Mathe (2016) are out of scope.

**Known items.** 8 of the 11 health research items and all 5 cross-disciplinary reviews on the search strategy page. Hutchings et al. (2020), Swales et al. (2024) and Inau et al. (2023) are missed; title terms for governance mechanisms would add 4,304 records to catch two of them.

**Added by hand.** Chiware and Mathe (2016), Hutchings et al. (2020), Swales et al. (2024) and Inau et al. (2023).

**Decisions.** Reuse leaves the review's question and the query. Factor terms guide screening. Sources that design, build or evaluate a system, product or service for sharing data are excluded. No document type filter, no citation searching. The seed sample and the stopping rule are still to be decided.
