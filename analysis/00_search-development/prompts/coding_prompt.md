You are coding a source for a scoping review. The review asks what factors influence the sharing and reuse of research data. Below are the fields to code, followed by the source's title and abstract. Code each field from the title and abstract only. Do not use anything you know about the source from elsewhere.

For each code, give:
- `value`: one of the values defined below
- `passage`: the sentence from the title or abstract that supports the value, copied exactly, or "none" when no sentence supports it
- `term`: the words in that passage that express the value, copied exactly, such as "secondary use" for reuse or "unwilling to share" for reluctance, or "none" when the passage expresses the value without a distinct term
- `location`: "title", "abstract" or "none"

## What to code

**practice**: what the source concerns.
- sharing: making research data available to others
- reuse: using research data that others generated
- both: sharing and reuse
- neither: neither sharing nor reuse of research data

**data_origin**: where the data the source concerns come from.
- research: data that researchers generate through procedures designed for a specific study, such as a trial, cohort, survey, experiment, interview study or fieldwork. Examples: trial measurements, survey responses, interview transcripts, sequencing data from study participants.
- not-research-data: data that public health agencies, health services or clinicians generate while conducting surveillance, delivering services or treating patients, and that stay within those activities. Examples: electronic health records used for treatment, disease registries used for surveillance, insurance claims used for billing, notifiable disease reports used for outbreak response.
- reused: not-research-data that researchers later obtain and analyse. Examples: electronic health records analysed in an observational study, registry data used in an epidemiological study.
- mixed: the source concerns research data and reused data, such as cohort data linked with health records.
- unclear: the source names the data but does not state who generated them or why.

**factors**: every factor the source reports that influences sharing or reuse. For each one, give as its `value` the entry from the list below that names the same factor. Decide by what the source reports, not by the words it uses. A list entry appearing in the text does not mean the source reports that factor, and a factor described without the words in the list still counts. For example, code reluctance for a source on researchers who withhold data for fear of losing credit, though it never uses that word. Give one code per factor reported. Give a single code with value "none" when the source reports no factor on the list.
- factors that obstruct: barriers, challenges, obstacles, reluctance, privacy
- factors that facilitate: facilitators, enablers, incentives, motivation, infrastructure, repositories, interoperability
- stakeholder perspectives: perceptions, attitudes, willingness
- policies and what drive them: policies, mandates, open science, open data, open access, open research
- mechanisms for implementation: governance, consent, licensing, ethics, stewardship, data management plans, data curation, digital curation

Each factor code also gives `theme`: the name of the group its value belongs to in the list above, such as "factors that obstruct" for reluctance.

**field**: the field of the research the source concerns.
- health: health research, including clinical, biomedical, public health, neuroscience and genetics research
- other: research in another single field
- cross-disciplinary: research across several fields

**source_type**:
- empirical: reports a study with its own data, such as a survey, interview study, experiment or analysis of records
- review: reviews or synthesises other studies
- policy-guidance: sets out a policy, guideline or recommendation
- opinion: argues a position, such as an editorial, commentary or letter
- other: anything else

**language**: the language of the title and abstract: "English", "French" or "other".

## Output

Answer with one JSON object and nothing else:

{"practice": {...code...}, "data_origin": {...code...}, "factors": [{...code with theme...}, ...], "field": {...code...}, "source_type": {...code...}, "language": "English"}

## Source

Title: {title}

Abstract: {abstract}
