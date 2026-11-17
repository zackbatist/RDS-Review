"""Functions and paths shared by the search development scripts in this folder."""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "search-development"
PROCESSED = ROOT / "data" / "processed" / "search-development"
PROCESSED_FILES = {"reference_sources.csv", "counts.csv", "verdict.csv", "statement_matches.csv",
                   "terms.csv", "term_syntax.csv"}
CODES = "reference_codes_qwen3.5-122b.csv"  # the local model's codes of record
DATABASES = {"pubmed": "PubMed", "scopus": "Scopus", "web-of-science": "Web of Science"}


def path(name):
    """Files notebook 00 builds are in PROCESSED; every other file is in RAW."""
    return (PROCESSED if name in PROCESSED_FILES else RAW) / name
EMAIL = "zachary.batist@mcgill.ca"
TODAY = datetime.date.today().isoformat()
BATCH = 25


def _get(url, params=None, headers=None, pause=0.0, tries=4):
    for i in range(tries):
        r = requests.get(url, params=params, headers=headers, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** i)
            continue
        r.raise_for_status()
        time.sleep(pause)
        return r
    r.raise_for_status()


# ---------- PubMed ----------
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def pubmed_search(q, retmax=0):
    p = dict(db="pubmed", term=q, retmax=retmax, retmode="json",
             api_key=os.environ["NCBI_API_KEY"], email=EMAIL, tool="rds-review")
    j = _get(EU + "esearch.fcgi", p, pause=0.11).json()["esearchresult"]
    return int(j["count"]), j.get("idlist", [])


def pubmed_all_ids(q):
    n, _ = pubmed_search(q)
    ids = []
    for start in range(0, n, 9999):
        p = dict(db="pubmed", term=q, retmax=9999, retstart=start, retmode="json",
                 api_key=os.environ["NCBI_API_KEY"], email=EMAIL, tool="rds-review")
        ids += _get(EU + "esearch.fcgi", p, pause=0.11).json()["esearchresult"]["idlist"]
    return ids


def pubmed_summary(ids):
    out = {}
    for i in range(0, len(ids), 200):
        p = dict(db="pubmed", id=",".join(ids[i:i + 200]), retmode="json",
                 api_key=os.environ["NCBI_API_KEY"], email=EMAIL, tool="rds-review")
        res = _get(EU + "esummary.fcgi", p, pause=0.11).json()["result"]
        for k in res.get("uids", []):
            r = res[k]
            doi = next((a["value"] for a in r.get("articleids", []) if a["idtype"] == "doi"), "")
            out[k] = dict(id=k, doi=doi.lower(), title=r.get("title", ""), year=r.get("pubdate", "")[:4])
    return out


# ---------- Scopus ----------
SC = "https://api.elsevier.com/content/search/scopus"


def scopus_search(q, count=25, start=0, cursor=None):
    h = {"X-ELS-APIKey": os.environ["SCOPUS_API_KEY"], "Accept": "application/json"}
    p = dict(query=q, count=count, view="STANDARD", field="eid,doi,title,coverDate")
    if cursor:
        p["cursor"] = cursor
    else:
        p["start"] = start
    r = _get(SC, p, h, pause=0.12)
    j = r.json()["search-results"]
    return j, r.headers


def scopus_count(q):
    j, _ = scopus_search(q, count=1)
    return int(j["opensearch:totalResults"])


def scopus_records(q, limit=None):
    recs, cursor = [], "*"
    while True:
        j, _ = scopus_search(q, count=200, cursor=cursor)
        ents = [e for e in j.get("entry", []) if "error" not in e]
        for e in ents:
            recs.append(dict(id=e.get("eid", ""), doi=e.get("prism:doi", "").lower(),
                             title=e.get("dc:title", ""), year=e.get("prism:coverDate", "")[:4]))
        nxt = j.get("cursor", {}).get("@next")
        if not ents or not nxt or nxt == cursor or (limit and len(recs) >= limit):
            return recs
        cursor = nxt


# ---------- Web of Science ----------
WS = "https://api.clarivate.com/apis/wos-starter/v1/documents"


def wos_search(q, limit=50, page=1):
    h = {"X-ApiKey": os.environ["WOS_API_KEY"]}
    p = dict(db="WOS", q=q, limit=limit, page=page)
    return _get(WS, p, h, pause=0.21).json()


def wos_count(q):
    return int(wos_search(q, limit=1)["metadata"]["total"])


def wos_records(q):
    recs, page = [], 1
    while True:
        j = wos_search(q, limit=50, page=page)
        for h in j.get("hits", []):
            recs.append(dict(id=h.get("uid", ""), doi=h.get("identifiers", {}).get("doi", "").lower(),
                             title=h.get("title", ""), year=str(h.get("source", {}).get("publishYear", ""))))
        if page * 50 >= j["metadata"]["total"] or not j.get("hits"):
            return recs
        page += 1


# ---------- database-neutral wrappers ----------
def date_limit(db, a, b):
    return {"PubMed": f"{a}:{b}[dp]",
            "Scopus": f"PUBYEAR > {a - 1} AND PUBYEAR < {b + 1}",
            "Web of Science": f"PY=({a}-{b})"}[db]


def id_clause(db, sources):
    """OR-joined identifier clause for a list of reference_sources rows."""
    parts = []
    for s in sources:
        if db == "PubMed":
            parts.append(f"{s['pmid']}[uid]" if s["pmid"] else f"{s['doi']}[doi]")
        elif db == "Scopus":
            parts.append(f"DOI({s['doi']})")
        else:
            parts.append(s["doi"])
    if db == "Web of Science":
        return "DO=(" + " OR ".join(parts) + ")"
    return "(" + " OR ".join(parts) + ")"


def testable(db, s):
    return bool(s["doi"]) or (db == "PubMed" and bool(s["pmid"]))


def count(db, q):
    return {"PubMed": lambda: pubmed_search(q)[0], "Scopus": lambda: scopus_count(q),
            "Web of Science": lambda: wos_count(q)}[db]()


def retrieved(db, q, sources):
    """Keys of sources in `sources` that query q retrieves, sending identifiers in batches."""
    hit = set()
    srcs = [s for s in sources if testable(db, s)]
    for i in range(0, len(srcs), BATCH):
        b = srcs[i:i + BATCH]
        full = f"({q}) AND {id_clause(db, b)}"
        if db == "PubMed":
            _, ids = pubmed_search(full, retmax=BATCH * 2)
            ids = set(ids)
            hit |= {s["key"] for s in b if s["pmid"] in ids}
            rest = [s for s in b if not s["pmid"]]
            if rest and ids:
                dois = {r["doi"] for r in pubmed_summary(list(ids)).values()}
                hit |= {s["key"] for s in rest if s["doi"].lower() in dois}
        elif db == "Scopus":
            dois = {r["doi"] for r in scopus_records(full)}
            hit |= {s["key"] for s in b if s["doi"].lower() in dois}
        else:
            dois = {r["doi"] for r in wos_records(full)}
            hit |= {s["key"] for s in b if s["doi"].lower() in dois}
    return hit


def records(db, q):
    if db == "PubMed":
        ids = pubmed_all_ids(q)
        return [dict(id=i) for i in ids]
    if db == "Scopus":
        return scopus_records(q)
    return wos_records(q)


def wilson(k, n, z=1.96):
    if n == 0:
        return ("", "", "")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (round(p, 3), round(max(0, c - h), 3), round(min(1, c + h), 3))


def read(name):
    return list(csv.DictReader(open(path(name), encoding="utf-8")))


def write(name, rows):
    path(name).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path(name).write_text("")
        return
    with open(path(name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
