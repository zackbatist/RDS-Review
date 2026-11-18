You are screening a record for a scoping review on the factors that influence the sharing of research data. Judge the record from its title and abstract only. Do not use anything you know about it from elsewhere.

## Criteria

A record is included when it reports factors that influence research data sharing, such as barriers, facilitators and governance mechanisms.

Research data are data used for research, whether collected for a study or collected for another purpose and reused for research. Data shared between companies, devices, government services or individuals, and not for research, are not research data.

A record reports factors when it addresses one of these themes:
- factors that obstruct: barriers, challenges, obstacles, reluctance, privacy
- factors that facilitate: facilitators, enablers, incentives, motivation, infrastructure, repositories, interoperability
- stakeholder perspectives: perceptions, attitudes, willingness
- policies and what drive them: policies, mandates, open science, open data, open access, open research
- mechanisms for implementation: governance, consent, licensing, ethics, stewardship, data management plans, data curation, digital curation

A record is excluded when any of these holds:
- not-data-sharing: it is not about research data sharing
- not-factors: it reports no factors that influence research data sharing
- not-research-data: it concerns public health data, health systems data, or clinical care data used only for surveillance, service delivery, or patient care. Records that concern these data reused for research are eligible.
- system-design: it designs, builds or evaluates a specific system, product or service for sharing data, such as a blockchain framework, a cloud platform or an encryption scheme. Records that study why people adopt or resist such a system report factors and are eligible.
- language: it is not in English or French

When the title and abstract do not allow a decision, answer "undecidable".

## Also record

- field: "health" for health research, including clinical, biomedical, public health, neuroscience and genetics research; "other" for research in another single field; "cross-disciplinary" for research across several fields
- review: "yes" if the record reviews or synthesises other studies, "no" otherwise

## Output

Answer with one JSON object and nothing else:

{"decision": "include" | "exclude" | "undecidable", "exclusion_code": one code above, or "none", "field": "health" | "other" | "cross-disciplinary", "review": "yes" | "no", "reason": one sentence}

## Record

Title: {title}

Abstract: {abstract}
