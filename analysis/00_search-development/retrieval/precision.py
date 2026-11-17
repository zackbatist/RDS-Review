"""Step 3 precision sample for one database, method item 10: draws 100 records from its load file and pulls their abstracts."""
import sys
from search_lib import *
from search_lib import _get

if len(sys.argv) != 2 or sys.argv[1] not in DATABASES:
    sys.exit("give one database: " + ", ".join(DATABASES))
DB = DATABASES[sys.argv[1]]
import xml.etree.ElementTree as ET
SEED = 20261112
slug = {"PubMed": "pubmed", "Scopus": "scopus", "Web of Science": "web-of-science"}[DB]
recs = read(f"load_{slug}.csv")
random.seed(SEED)
sample = random.sample(recs, min(100, len(recs)))


def pubmed_abstracts(ids):
    out = {}
    for i in range(0, len(ids), 200):
        p = dict(db="pubmed", id=",".join(ids[i:i + 200]), retmode="xml",
                 api_key=os.environ["NCBI_API_KEY"], email=EMAIL, tool="rds-review")
        root = ET.fromstring(_get(EU + "efetch.fcgi", p, pause=0.11).content)
        for a in root.iter("PubmedArticle"):
            out[a.findtext(".//PMID")] = " ".join("".join(t.itertext()) for t in a.findall(".//AbstractText"))
    return out


pm_abs = pubmed_abstracts([r["id"] for r in sample]) if DB == "PubMed" else {}


def openalex_abstract(doi):
    if not doi:
        return ""
    try:
        j = _get(f"https://api.openalex.org/works/doi:{doi}",
                 dict(select="abstract_inverted_index", mailto=EMAIL), pause=0.1).json()
    except requests.HTTPError:
        return ""
    inv = j.get("abstract_inverted_index") or {}
    pos = {p: w for w, ps in inv.items() for p in ps}
    return " ".join(pos[i] for i in sorted(pos))


def crossref_abstract(doi):
    if not doi:
        return ""
    try:
        j = _get(f"https://api.crossref.org/works/{doi}", dict(mailto=EMAIL), pause=0.1).json()
    except requests.HTTPError:
        return ""
    return re.sub(r"<[^>]+>", " ", j["message"].get("abstract", "")).strip()


def scopus_abstract(eid):
    h = {"X-ELS-APIKey": os.environ["SCOPUS_API_KEY"], "Accept": "application/json"}
    try:
        j = _get(f"https://api.elsevier.com/content/abstract/eid/{eid}", dict(view="META_ABS"), h, pause=0.2).json()
    except requests.HTTPError:
        return ""
    return (j.get("abstracts-retrieval-response", {}).get("coredata", {}).get("dc:description") or "").strip()


def pubmed_abstract_by_doi(doi):
    if not doi:
        return ""
    n, ids = pubmed_search(f"{doi}[doi]", retmax=2)
    return pubmed_abstracts(ids).get(ids[0], "") if n == 1 else ""


def scopus_abstract_by_doi(doi):
    if not doi:
        return ""
    h = {"X-ELS-APIKey": os.environ["SCOPUS_API_KEY"], "Accept": "application/json"}
    try:
        j = _get(f"https://api.elsevier.com/content/abstract/doi/{doi}", dict(view="META_ABS"), h, pause=0.2).json()
    except requests.HTTPError:
        return ""
    return (j.get("abstracts-retrieval-response", {}).get("coredata", {}).get("dc:description") or "").strip()


rows = []
for r in sample:
    a, srcname = pm_abs.get(r["id"], ""), "database"
    if not a:
        a = openalex_abstract(r.get("doi", ""))
        srcname = "OpenAlex" if a else ""
    if not a:
        a = crossref_abstract(r.get("doi", ""))
        srcname = "Crossref" if a else ""
    if not a and DB == "Scopus":
        a = scopus_abstract(r["id"])
        srcname = "database" if a else ""
    if not a and DB == "Web of Science":  # the Web of Science Starter API returns no abstracts
        a = pubmed_abstract_by_doi(r.get("doi", ""))
        srcname = "PubMed" if a else ""
        if not a:
            a = scopus_abstract_by_doi(r.get("doi", ""))
            srcname = "Scopus" if a else ""
    srcname = srcname or "none"
    rows.append(dict(record_id=r["id"], doi=r.get("doi", ""), title=r.get("title", ""), year=r.get("year", ""),
                     abstract_source=srcname, abstract=a, decision="", exclusion_code=""))
    print(r["id"], srcname, flush=True)
write(f"precision_sample_{slug}.csv", rows)
tests = read("query_tests.csv")
for t in tests:
    if t["database"] == DB:
        t["seed"] = SEED
write("query_tests.csv", tests)
print(f"seed {SEED}; {len(rows)} records; no abstract for {sum(r['abstract_source'] == 'none' for r in rows)}")
