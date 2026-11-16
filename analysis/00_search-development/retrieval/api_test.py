"""API test: checks that each API answers and that the DOI and field tags behave, and shows the Scopus weekly quota left. Expect Fecher et al. (2015) found once in each database."""
from search_lib import *
DOI = "10.1371/journal.pone.0118053"
print("PubMed")
print("  doi:", pubmed_search(f"{DOI}[doi]", retmax=5))
print("  [tiab]:", pubmed_search(f'"data sharing"[tiab] AND {DOI}[doi]', retmax=5))
print("  [mh:noexp]:", pubmed_search(f'"Information Dissemination"[mh:noexp] AND {DOI}[doi]', retmax=5))
print("  date limit:", pubmed_search(f'"data sharing"[tiab] AND {date_limit("PubMed", 2007, 2014)}')[0])
print("Scopus")
j, h = scopus_search(f'TITLE-ABS-KEY("data sharing") AND DOI({DOI})')
print("  hits:", j["opensearch:totalResults"], [e.get("dc:title") for e in j.get("entry", []) if "error" not in e])
print("  date limit:", scopus_count(f'TITLE-ABS-KEY("data sharing") AND {date_limit("Scopus", 2007, 2014)}'))
print("  X-RateLimit-Remaining:", h.get("X-RateLimit-Remaining"), "of", h.get("X-RateLimit-Limit"))
print("Web of Science")
j = wos_search(f'TS=("data sharing") AND DO=({DOI})')
print("  hits:", j["metadata"]["total"], [x.get("title") for x in j.get("hits", [])])
print("  date limit:", wos_count(f'TS=("data sharing") AND {date_limit("Web of Science", 2007, 2014)}'))
