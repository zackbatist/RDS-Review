"""Step 1 lookups, Reference set item 2: DOIs, PMIDs, dates, titles, abstracts, MeSH headings with scope notes, author keywords and OpenAlex keywords for the reference set."""
import csv, difflib, os, re, time, unicodedata
import xml.etree.ElementTree as ET
import requests
from search_lib import path

EMAIL = "zachary.batist@mcgill.ca"
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
NCBI = dict(api_key=os.environ["NCBI_API_KEY"], email=EMAIL, tool="rds-review")
ELS = {"X-ELS-APIKey": os.environ["SCOPUS_API_KEY"], "Accept": "application/json"}
fold = lambda s: re.sub(r"[^a-z0-9 ]", " ", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())
same_title = lambda a, b: difflib.SequenceMatcher(None, " ".join(fold(a).split()), " ".join(fold(b).split())).ratio() >= 0.9


def get(url, params=None, headers=None, pause=0.12):
    for i in range(4):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=60)
        except requests.RequestException:
            time.sleep(2 ** i)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** i)
            continue
        time.sleep(pause)
        return r
    return None


def ok(r):
    return r is not None and r.status_code == 200


def openalex_by_doi(doi):
    r = get(f"https://api.openalex.org/works/doi:{doi}", dict(mailto=EMAIL))
    return r.json() if ok(r) else {}


def openalex_by_title(title, year, author):
    r = get("https://api.openalex.org/works", dict(search=title, per_page=10, mailto=EMAIL))
    if not ok(r):
        return {}
    for w in r.json().get("results", []):
        y = w.get("publication_year") or 0
        names = " ".join(fold(a["author"]["display_name"]) for a in w.get("authorships", []))
        if same_title(w.get("title") or "", title) and (not year or abs(y - int(year)) <= 1) and fold(author).split()[:1] and fold(author).split()[0] in names:
            return w
    return {}


def crossref(doi):
    r = get(f"https://api.crossref.org/works/{doi}", dict(mailto=EMAIL))
    return r.json()["message"] if ok(r) else {}


def crossref_date(m):
    ds = []
    for k in ("published-online", "published-print", "issued"):
        p = (m.get(k) or {}).get("date-parts", [[None]])[0]
        if p and p[0]:
            ds.append("-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(p)))
    return min(ds) if ds else ""


def openalex_abstract(w):
    inv = w.get("abstract_inverted_index") or {}
    pos = {p: x for x, ps in inv.items() for p in ps}
    return " ".join(pos[i] for i in sorted(pos))


MONTHS = {m: f"{i:02d}" for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def pubmed(pmid):
    r = get(EU + "efetch.fcgi", dict(db="pubmed", id=pmid, retmode="xml", **NCBI))
    if not ok(r):
        return {}
    a = ET.fromstring(r.content).find(".//PubmedArticle")
    if a is None:
        return {}
    dates = []
    for d in a.findall(".//ArticleDate") + a.findall(".//PubDate"):
        y, m, dd = d.findtext("Year"), d.findtext("Month") or "", d.findtext("Day") or ""
        if y:
            dates.append("-".join(v.zfill(2) for v in (y, MONTHS.get(m[:3], m), dd) if v))
    return dict(abstract=" ".join("".join(t.itertext()) for t in a.findall(".//AbstractText")).strip(),
                mesh=[m.findtext("DescriptorName") for m in a.findall(".//MeshHeading")],
                keywords=["".join(k.itertext()).strip() for k in a.findall(".//Keyword")],
                date=min(dates) if dates else "")


def pmid_for(doi, title):
    term = f"{doi}[doi]" if doi else f"{title}[ti]"
    r = get(EU + "esearch.fcgi", dict(db="pubmed", term=term, retmode="json", **NCBI))
    ids = r.json()["esearchresult"]["idlist"] if ok(r) else []
    return ids[0] if len(ids) == 1 else ""


def scopus_abstract(doi):
    r = get(f"https://api.elsevier.com/content/abstract/doi/{doi}", dict(view="META_ABS"), ELS, pause=0.2)
    if not ok(r):
        return ""
    return (r.json().get("abstracts-retrieval-response", {}).get("coredata", {}).get("dc:description") or "").strip()


refs = list(csv.DictReader(open(path("reference_candidates.csv"), encoding="utf-8")))
lookups, indexing = [], []
for x in refs:
    doi = x["doi"].lower()
    status = ""
    w = {}
    if doi:
        cr = crossref(doi)
        w = openalex_by_doi(doi)
        status = "Crossref" if cr else ("OpenAlex" if w else "not found")
    else:
        cr = {}
        w = openalex_by_title(x["title"], x["year"], x["first_author"])
        if w.get("doi"):
            doi = w["doi"].replace("https://doi.org/", "").lower()
            cr = crossref(doi)
            status = "found by title"
        else:
            status = "no DOI"
    pmid = pmid_for(doi, x["title"])
    pm = pubmed(pmid) if pmid else {}
    title = x["title"] or w.get("title") or (cr.get("title") or [""])[0]
    abstract, source = pm.get("abstract", ""), "PubMed"
    if not abstract:
        abstract, source = openalex_abstract(w), "OpenAlex"
    if not abstract:
        abstract, source = re.sub(r"<[^>]+>", " ", cr.get("abstract", "")).strip(), "Crossref"
    if not abstract and doi:
        abstract, source = scopus_abstract(doi), "Scopus"
    if not abstract:
        source = "none"
    dates = [d for d in (pm.get("date", ""), w.get("publication_date") or "", crossref_date(cr)) if d]
    lookups.append(dict(ref_id=x["ref_id"], first_author=x["first_author"], year_cited=x["year"], doi=doi,
                        doi_status=status, pmid=pmid, openalex_id=(w.get("id") or "").rsplit("/", 1)[-1],
                        title=title, pub_date=min(dates) if dates else "", abstract_source=source, abstract=abstract))
    for term in pm.get("mesh", []):
        indexing.append(dict(ref_id=x["ref_id"], type="MeSH", term=term))
    for term in pm.get("keywords", []):
        indexing.append(dict(ref_id=x["ref_id"], type="author keyword", term=term))
    for k in w.get("keywords", []) or []:
        indexing.append(dict(ref_id=x["ref_id"], type="OpenAlex keyword", term=k.get("display_name", "")))
    print(f"{x['first_author']} {x['year']}: {status}, PMID {pmid or '-'}, abstract {source}", flush=True)

# NLM scope notes for every MeSH heading
notes = {}
for h in sorted({i["term"] for i in indexing if i["type"] == "MeSH"}):
    r = get(EU + "esearch.fcgi", dict(db="mesh", term=f'"{h}"[MH]', retmode="json", **NCBI))
    ids = r.json()["esearchresult"]["idlist"] if ok(r) else []
    if ids:
        s = get(EU + "esummary.fcgi", dict(db="mesh", id=ids[0], retmode="json", **NCBI))
        notes[h] = (s.json()["result"][ids[0]].get("ds_scopenote") or "").strip() if ok(s) else ""
for i in indexing:
    i["scope_note"] = notes.get(i["term"], "") if i["type"] == "MeSH" else ""


def write(name, data):
    with open(path(name), "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
        wr.writeheader()
        wr.writerows(data)


write("reference_lookups.csv", lookups)
write("reference_indexing.csv", indexing)
count = lambda key: {v: sum(1 for l in lookups if l[key] == v) for v in sorted({l[key] for l in lookups})}
print("\nreferences:", len(lookups))
print("DOI status:", count("doi_status"))
print("with PMID:", sum(1 for l in lookups if l["pmid"]))
print("abstract source:", count("abstract_source"))
print("indexing terms:", {t: sum(1 for i in indexing if i["type"] == t) for t in ("MeSH", "author keyword", "OpenAlex keyword")})
print("MeSH headings with a scope note:", sum(1 for v in notes.values() if v), "of", len(notes))
