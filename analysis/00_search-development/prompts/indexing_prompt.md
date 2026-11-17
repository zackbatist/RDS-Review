You are sorting indexing terms for a scoping review. The review asks what factors influence the sharing and reuse of research data. The term below is a MeSH heading, an author keyword or an OpenAlex keyword. Give it the value below that matches what it means.

Decide by meaning, not by the words in the term. Give a term containing "sharing" the value sharing only if it means making research data available to others. Give a term that names a factor without using the word in the list that factor as its value. For example, give "data withholding" the value reluctance.

## Values

- sharing: the term names the act of making research data available to others
- reuse: the term names the act of using research data that others generated
- a factor from this list, when the term names that factor:
  - factors that obstruct: barriers, challenges, obstacles, reluctance, privacy
  - factors that facilitate: facilitators, enablers, incentives, motivation, infrastructure, repositories, interoperability
  - stakeholder perspectives: perceptions, attitudes, willingness
  - policies and what drive them: policies, mandates, open science, open data, open access, open research
  - mechanisms for implementation: governance, consent, licensing, ethics, stewardship, data management plans, data curation, digital curation
- none: the term names a topic, method, place, population, discipline or anything else outside these values

For a MeSH heading, its NLM scope note is given; assign by the scope note.

## Output

Answer with one JSON object and nothing else, with the term's value as a string:

{"value": "sharing"}

## Term

{term}
