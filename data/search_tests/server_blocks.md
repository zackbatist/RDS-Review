# Server blocks

Paste each block into a terminal on the analysis server. Each block moves into the repository, pulls, activates the environment, loads the keys and runs Python from a heredoc; nothing is saved as a `.py` file.

**Check before running:** the blocks assume the repository is cloned at `~/RDS-Review`. If it lives elsewhere, change the `cd` line in every block.

**Run the long blocks inside `tmux`** (`tmux new -s search`, then paste; detach with Ctrl-b d, reattach with `tmux attach -t search`), so a dropped connection doesn't stop them. Each block also writes its console output to `data/search_tests/`.

Order: blocks 1 to 3 once; block 4 and check its output; blocks 5 to 7 (one per database, any order, one at a time); blocks 8 to 10 after the matching query block, once `load_<database>.csv` exists. The real review exports come later, from each database's own interface as RIS files named as `data/raw/search_exports/README.md` sets out.

## 1. Keys file

Prompts for each key without echoing it, writes `~/.rds-review-keys` outside the repository, readable by you only.

```bash
umask 077
read -rsp "NCBI API key: " NCBI; echo
read -rsp "Scopus API key: " SCOPUS; echo
read -rsp "Web of Science Starter API key: " WOS; echo
printf 'export NCBI_API_KEY=%s\nexport SCOPUS_API_KEY=%s\nexport WOS_API_KEY=%s\n' "$NCBI" "$SCOPUS" "$WOS" > ~/.rds-review-keys
chmod 600 ~/.rds-review-keys
unset NCBI SCOPUS WOS
grep -q rds-review-keys ~/.bashrc || echo 'source ~/.rds-review-keys' >> ~/.bashrc
ls -l ~/.rds-review-keys
```

## 2. Python environment

```bash
cd ~/RDS-Review
git pull
python3 -m venv ~/.venvs/rds-review
source ~/.venvs/rds-review/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 -c "import requests; print('requests', requests.__version__)"
```

## 3. Check the step 1 and 2 files

Unzip `RDS-Review-search-development.zip` at the repository root, then check that `term_syntax.csv` and the other step 1 and 2 files sit in `data/search_tests/`:

```bash
cd ~/RDS-Review
ls data/search_tests/
python3 -c "import csv; print(sum(1 for _ in csv.DictReader(open('data/search_tests/term_syntax.csv'))), 'term_syntax rows')"
```

## 4. Test block

Checks each API answers, the DOI and field tags behave, and shows the Scopus weekly quota left. Expect Fecher et al. (2015) found once in each database. If a line errors, stop and send me the output.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 1h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/api_test_console.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "PubMed"

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

PYEOF
```

## 5. Query block: PubMed

Runs plan step 3, method items 3 to 9 for PubMed: term runs, yield threshold, draft, trim, index check, test set coverage and load. In `data/search_tests/`, it writes `query_runs_pubmed.csv` and `load_pubmed.csv`, replaces the PubMed rows of `query_tests.csv` and `query_misses.csv`, and fills the step 3 columns of the PubMed *sharing* and *reuse* rows in `terms.csv`. Expect one to several hours; each candidate costs one count, one load count and two or three identifier batches, and each draft round one query per remaining candidate.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 10h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/query_console_pubmed.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "PubMed"
# ---------- query block: plan step 3, method items 3 to 9 ----------
import collections
src = read("reference_sources.csv")
syn = {(r["term"], r["type"], r["database"]): r["written_form"] for r in read("term_syntax.csv")}
terms = read("terms.csv")
dev = [s for s in src if s["set"] == "development" and s["eligible_apart_from_year"] == "yes"]
test = [s for s in src if s["set"] == "test"]
log = []

cand = [t for t in terms if t["database"] == DB and t["pcc_part"] in ("sharing", "reuse")]
cand.sort(key=lambda t: t["type"] != "fallback")  # a fallback term keeps its status when another term writes the same string
seen, uniq = set(), []
for t in cand:
    k = syn[(t["term"], t["type"], DB)]
    if k not in seen:
        seen.add(k)
        uniq.append(t)
cand = uniq
fallback = [t for t in cand if t["type"] == "fallback"]
regular = [t for t in cand if t["type"] != "fallback"]


def wf(t):
    return syn[(t["term"], t["type"], DB)]


def q_of(ts):
    return " OR ".join(f"({wf(t)})" for t in ts)


DEV_SPAN = date_limit(DB, 2007, 2014)
REVIEW_SPAN = date_limit(DB, 2015, 2025)


def measure(ts):
    q = q_of(ts)
    recs = count(DB, f"({q}) AND {DEV_SPAN}")
    hits = retrieved(DB, q, dev)
    return q, recs, hits


# item 3: term runs
runs = {}
for t in cand:
    q, recs, hits = measure([t])
    load = count(DB, f"({q}) AND {REVIEW_SPAN}")
    y = round(1000 * len(hits) / recs, 3) if recs else 0
    runs[(t["term"], t["type"])] = dict(t=t, recs=recs, hits=hits, load=load, y=y)
    log.append(dict(step="term run", term=t["term"], type=t["type"], records_2007_2014=recs,
                    dev_sources=len(hits), yield_per_1000=y, load_2015_2025=load, keys=";".join(sorted(hits))))
    print("term run", t["term"], recs, len(hits), load, flush=True)

# item 4: threshold
q_all, recs_all, hits_all = measure(regular)
threshold = round(1000 * len(hits_all) / recs_all, 3) if recs_all else 0
log.append(dict(step="threshold", term="(all regular candidates)", type="", records_2007_2014=recs_all,
                dev_sources=len(hits_all), yield_per_1000=threshold, load_2015_2025="", keys=";".join(sorted(hits_all))))
print("threshold", threshold, flush=True)

# item 5: draft
status = {}
start = max(regular, key=lambda t: (len(runs[(t["term"], t["type"])]["hits"]), -runs[(t["term"], t["type"])]["recs"], t["term"]))
draft = [start]
added_at_entry = {(start["term"], start["type"]): len(runs[(start["term"], start["type"])]["hits"])}
_, d_recs, d_hits = measure(draft)
log.append(dict(step="draft start", term=start["term"], type=start["type"], records_2007_2014=d_recs,
                dev_sources=len(d_hits), yield_per_1000="", load_2015_2025="", keys=""))
rest = [t for t in regular if t is not start]
while rest:
    options = []
    for t in rest:
        r = runs[(t["term"], t["type"])]
        if not (r["hits"] - d_hits):
            continue
        _, recs, hits = measure(draft + [t])
        s_add, r_add = len(hits - d_hits), max(recs - d_recs, 0)
        y_add = 1000 * s_add / r_add if r_add else float("inf")
        options.append((-y_add, r_add, t["term"], t, recs, hits, s_add))
    options.sort(key=lambda o: (o[0], o[1], o[2]))
    best = None
    if options:
        o = options[0]
        best = (-o[0], None, None, o[3], o[4], o[5], o[6], o[1])
    if not best or best[0] < threshold:
        break
    y_add, _, _, t, recs, hits, s_add, r_add = best
    draft.append(t)
    added_at_entry[(t["term"], t["type"])] = s_add
    log.append(dict(step="draft add", term=t["term"], type=t["type"], records_2007_2014=recs,
                    dev_sources=len(hits), yield_per_1000=round(y_add, 3) if y_add != float("inf") else "inf",
                    load_2015_2025="", keys=f"added {s_add} sources for {r_add} records"))
    d_recs, d_hits = recs, hits
    rest = [x for x in rest if x is not t]
    print("added", t["term"], flush=True)
for t in rest:
    status[(t["term"], t["type"])] = "excluded by yield"
for t in fallback:
    draft.append(t)
    status[(t["term"], t["type"])] = "fallback in query"

# item 6: trim
for t in sorted([t for t in draft if t["type"] != "fallback"], key=lambda t: added_at_entry[(t["term"], t["type"])]):
    if len(draft) == 1:
        break
    trial = [x for x in draft if x is not t]
    hits = retrieved(DB, q_of(trial), dev)
    if hits == d_hits:
        draft = trial
        status[(t["term"], t["type"])] = "excluded by yield"
        log.append(dict(step="trim drop", term=t["term"], type=t["type"], records_2007_2014="", dev_sources=len(hits),
                        yield_per_1000="", load_2015_2025="", keys=""))
for t in draft:
    status.setdefault((t["term"], t["type"]), "in query")
final_q = q_of(draft)
_, f_recs, f_hits = measure(draft)

# items 7 and 8: index check and coverage on the test set
idx = set()
for i in range(0, len([s for s in test if testable(DB, s)]), BATCH):
    b = [s for s in test if testable(DB, s)][i:i + BATCH]
    clause = id_clause(DB, b)
    if DB == "PubMed":
        _, ids = pubmed_search(clause, retmax=BATCH * 2)
        idx |= {s["key"] for s in b if s["pmid"] in set(ids)}
        rest_b = [s for s in b if not s["pmid"]]
        if rest_b and ids:
            dois = {r["doi"] for r in pubmed_summary(ids).values()}
            idx |= {s["key"] for s in rest_b if s["doi"].lower() in dois}
    elif DB == "Scopus":
        dois = {r["doi"] for r in scopus_records(clause)}
        idx |= {s["key"] for s in b if s["doi"].lower() in dois}
    else:
        dois = {r["doi"] for r in wos_records(clause)}
        idx |= {s["key"] for s in b if s["doi"].lower() in dois}
untestable = [s["key"] for s in test if not testable(DB, s)]
idx_src = [s for s in test if s["key"] in idx]
cov = retrieved(DB, final_q, idx_src)
in_scope_idx = [s for s in idx_src if s["in_scope"] == "yes"]
cov_all = wilson(len(cov), len(idx_src))
cov_in = wilson(len([s for s in in_scope_idx if s["key"] in cov]), len(in_scope_idx))

# item 9: load
slug = {"PubMed": "pubmed", "Scopus": "scopus", "Web of Science": "web-of-science"}[DB]
load_q = f"({final_q}) AND {REVIEW_SPAN}"
recs = records(DB, load_q)
if DB == "PubMed":
    meta = pubmed_summary([r["id"] for r in recs])
    recs = [meta.get(r["id"], dict(id=r["id"], doi="", title="", year="")) for r in recs]
write(f"load_{slug}.csv", recs)
write(f"query_runs_{slug}.csv", log)


def upsert(name, rows):
    """Replace this database's rows in a file shared by the three databases."""
    old = [r for r in read(name) if r["database"] != DB] if (T / name).exists() and (T / name).stat().st_size else []
    write(name, old + rows)


upsert("query_tests.csv", [dict(
    database=DB, final_query=final_q, date_run=TODAY, yield_threshold=threshold,
    development_yield=round(1000 * len(f_hits) / f_recs, 3) if f_recs else 0, load=len(recs),
    test_indexed=len(idx_src), test_untestable=len(untestable), test_retrieved=len(cov),
    coverage_test=cov_all[0], coverage_test_ci=f"{cov_all[1]}-{cov_all[2]}",
    coverage_in_scope=cov_in[0], coverage_in_scope_ci=f"{cov_in[1]}-{cov_in[2]}",
    seed="", sample_included="", sample_excluded="", sample_undecidable="", sample_title_only="",
    precision_undecidable_included="", precision_undecidable_included_ci="",
    precision_undecidable_left_out="", precision_undecidable_left_out_ci="",
    note="test set ends in July 2018, so coverage of vocabulary from later years is untested")])

# query_misses.csv: indexed test set sources not retrieved; development sources reached only by excluded terms
codes = read("reference_codes.csv")
pterms = collections.defaultdict(list)
for c in codes:
    if c["field"] == "Practice" and c["term"]:
        pterms[c["key"]].append(c["term"])
by_key = {s["key"]: s for s in src}
excluded = [t for t in regular if status.get((t["term"], t["type"])) == "excluded by yield"]
reach = collections.defaultdict(list)
for t in excluded:
    for k in runs[(t["term"], t["type"])]["hits"]:
        reach[k].append(t["term"])
miss = [s for s in idx_src if s["key"] not in cov] + [by_key[k] for k in sorted(set(reach) - f_hits)]
upsert("query_misses.csv", [dict(
    database=DB, doi=s["doi"], title=s["title"], set=s["set"], in_scope=s["in_scope"],
    sharing_reuse_terms="; ".join(pterms[s["key"]]), excluded_term="; ".join(reach.get(s["key"], [])))
    for s in miss])

# terms.csv: fill the step 3 columns for this database's sharing and reuse rows
by_form = {wf(t): (t["term"], t["type"]) for t in cand}
rows = read("terms.csv")
for r in rows:
    if r["database"] != DB or r["pcc_part"] not in ("sharing", "reuse"):
        continue
    k = by_form[syn[(r["term"], r["type"], DB)]]
    r["development_yield"] = runs[k]["y"]
    r["load_2015_2025"] = runs[k]["load"]
    r["sources_added"] = added_at_entry.get(k, "") if status.get(k) in ("in query", "fallback in query") else ""
    r["status"] = status.get(k, "excluded by yield")
write("terms.csv", rows)
print("final query:", final_q)
print("load", len(recs), "coverage", cov_all, "in scope", cov_in)

PYEOF
```

## 6. Query block: Scopus

Runs plan step 3, method items 3 to 9 for Scopus: term runs, yield threshold, draft, trim, index check, test set coverage and load. In `data/search_tests/`, it writes `query_runs_scopus.csv` and `load_scopus.csv`, replaces the Scopus rows of `query_tests.csv` and `query_misses.csv`, and fills the step 3 columns of the Scopus *sharing* and *reuse* rows in `terms.csv`. Expect one to several hours; each candidate costs one count, one load count and two or three identifier batches, and each draft round one query per remaining candidate.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 10h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/query_console_scopus.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "Scopus"
# ---------- query block: plan step 3, method items 3 to 9 ----------
import collections
src = read("reference_sources.csv")
syn = {(r["term"], r["type"], r["database"]): r["written_form"] for r in read("term_syntax.csv")}
terms = read("terms.csv")
dev = [s for s in src if s["set"] == "development" and s["eligible_apart_from_year"] == "yes"]
test = [s for s in src if s["set"] == "test"]
log = []

cand = [t for t in terms if t["database"] == DB and t["pcc_part"] in ("sharing", "reuse")]
cand.sort(key=lambda t: t["type"] != "fallback")  # a fallback term keeps its status when another term writes the same string
seen, uniq = set(), []
for t in cand:
    k = syn[(t["term"], t["type"], DB)]
    if k not in seen:
        seen.add(k)
        uniq.append(t)
cand = uniq
fallback = [t for t in cand if t["type"] == "fallback"]
regular = [t for t in cand if t["type"] != "fallback"]


def wf(t):
    return syn[(t["term"], t["type"], DB)]


def q_of(ts):
    return " OR ".join(f"({wf(t)})" for t in ts)


DEV_SPAN = date_limit(DB, 2007, 2014)
REVIEW_SPAN = date_limit(DB, 2015, 2025)


def measure(ts):
    q = q_of(ts)
    recs = count(DB, f"({q}) AND {DEV_SPAN}")
    hits = retrieved(DB, q, dev)
    return q, recs, hits


# item 3: term runs
runs = {}
for t in cand:
    q, recs, hits = measure([t])
    load = count(DB, f"({q}) AND {REVIEW_SPAN}")
    y = round(1000 * len(hits) / recs, 3) if recs else 0
    runs[(t["term"], t["type"])] = dict(t=t, recs=recs, hits=hits, load=load, y=y)
    log.append(dict(step="term run", term=t["term"], type=t["type"], records_2007_2014=recs,
                    dev_sources=len(hits), yield_per_1000=y, load_2015_2025=load, keys=";".join(sorted(hits))))
    print("term run", t["term"], recs, len(hits), load, flush=True)

# item 4: threshold
q_all, recs_all, hits_all = measure(regular)
threshold = round(1000 * len(hits_all) / recs_all, 3) if recs_all else 0
log.append(dict(step="threshold", term="(all regular candidates)", type="", records_2007_2014=recs_all,
                dev_sources=len(hits_all), yield_per_1000=threshold, load_2015_2025="", keys=";".join(sorted(hits_all))))
print("threshold", threshold, flush=True)

# item 5: draft
status = {}
start = max(regular, key=lambda t: (len(runs[(t["term"], t["type"])]["hits"]), -runs[(t["term"], t["type"])]["recs"], t["term"]))
draft = [start]
added_at_entry = {(start["term"], start["type"]): len(runs[(start["term"], start["type"])]["hits"])}
_, d_recs, d_hits = measure(draft)
log.append(dict(step="draft start", term=start["term"], type=start["type"], records_2007_2014=d_recs,
                dev_sources=len(d_hits), yield_per_1000="", load_2015_2025="", keys=""))
rest = [t for t in regular if t is not start]
while rest:
    options = []
    for t in rest:
        r = runs[(t["term"], t["type"])]
        if not (r["hits"] - d_hits):
            continue
        _, recs, hits = measure(draft + [t])
        s_add, r_add = len(hits - d_hits), max(recs - d_recs, 0)
        y_add = 1000 * s_add / r_add if r_add else float("inf")
        options.append((-y_add, r_add, t["term"], t, recs, hits, s_add))
    options.sort(key=lambda o: (o[0], o[1], o[2]))
    best = None
    if options:
        o = options[0]
        best = (-o[0], None, None, o[3], o[4], o[5], o[6], o[1])
    if not best or best[0] < threshold:
        break
    y_add, _, _, t, recs, hits, s_add, r_add = best
    draft.append(t)
    added_at_entry[(t["term"], t["type"])] = s_add
    log.append(dict(step="draft add", term=t["term"], type=t["type"], records_2007_2014=recs,
                    dev_sources=len(hits), yield_per_1000=round(y_add, 3) if y_add != float("inf") else "inf",
                    load_2015_2025="", keys=f"added {s_add} sources for {r_add} records"))
    d_recs, d_hits = recs, hits
    rest = [x for x in rest if x is not t]
    print("added", t["term"], flush=True)
for t in rest:
    status[(t["term"], t["type"])] = "excluded by yield"
for t in fallback:
    draft.append(t)
    status[(t["term"], t["type"])] = "fallback in query"

# item 6: trim
for t in sorted([t for t in draft if t["type"] != "fallback"], key=lambda t: added_at_entry[(t["term"], t["type"])]):
    if len(draft) == 1:
        break
    trial = [x for x in draft if x is not t]
    hits = retrieved(DB, q_of(trial), dev)
    if hits == d_hits:
        draft = trial
        status[(t["term"], t["type"])] = "excluded by yield"
        log.append(dict(step="trim drop", term=t["term"], type=t["type"], records_2007_2014="", dev_sources=len(hits),
                        yield_per_1000="", load_2015_2025="", keys=""))
for t in draft:
    status.setdefault((t["term"], t["type"]), "in query")
final_q = q_of(draft)
_, f_recs, f_hits = measure(draft)

# items 7 and 8: index check and coverage on the test set
idx = set()
for i in range(0, len([s for s in test if testable(DB, s)]), BATCH):
    b = [s for s in test if testable(DB, s)][i:i + BATCH]
    clause = id_clause(DB, b)
    if DB == "PubMed":
        _, ids = pubmed_search(clause, retmax=BATCH * 2)
        idx |= {s["key"] for s in b if s["pmid"] in set(ids)}
        rest_b = [s for s in b if not s["pmid"]]
        if rest_b and ids:
            dois = {r["doi"] for r in pubmed_summary(ids).values()}
            idx |= {s["key"] for s in rest_b if s["doi"].lower() in dois}
    elif DB == "Scopus":
        dois = {r["doi"] for r in scopus_records(clause)}
        idx |= {s["key"] for s in b if s["doi"].lower() in dois}
    else:
        dois = {r["doi"] for r in wos_records(clause)}
        idx |= {s["key"] for s in b if s["doi"].lower() in dois}
untestable = [s["key"] for s in test if not testable(DB, s)]
idx_src = [s for s in test if s["key"] in idx]
cov = retrieved(DB, final_q, idx_src)
in_scope_idx = [s for s in idx_src if s["in_scope"] == "yes"]
cov_all = wilson(len(cov), len(idx_src))
cov_in = wilson(len([s for s in in_scope_idx if s["key"] in cov]), len(in_scope_idx))

# item 9: load
slug = {"PubMed": "pubmed", "Scopus": "scopus", "Web of Science": "web-of-science"}[DB]
load_q = f"({final_q}) AND {REVIEW_SPAN}"
recs = records(DB, load_q)
if DB == "PubMed":
    meta = pubmed_summary([r["id"] for r in recs])
    recs = [meta.get(r["id"], dict(id=r["id"], doi="", title="", year="")) for r in recs]
write(f"load_{slug}.csv", recs)
write(f"query_runs_{slug}.csv", log)


def upsert(name, rows):
    """Replace this database's rows in a file shared by the three databases."""
    old = [r for r in read(name) if r["database"] != DB] if (T / name).exists() and (T / name).stat().st_size else []
    write(name, old + rows)


upsert("query_tests.csv", [dict(
    database=DB, final_query=final_q, date_run=TODAY, yield_threshold=threshold,
    development_yield=round(1000 * len(f_hits) / f_recs, 3) if f_recs else 0, load=len(recs),
    test_indexed=len(idx_src), test_untestable=len(untestable), test_retrieved=len(cov),
    coverage_test=cov_all[0], coverage_test_ci=f"{cov_all[1]}-{cov_all[2]}",
    coverage_in_scope=cov_in[0], coverage_in_scope_ci=f"{cov_in[1]}-{cov_in[2]}",
    seed="", sample_included="", sample_excluded="", sample_undecidable="", sample_title_only="",
    precision_undecidable_included="", precision_undecidable_included_ci="",
    precision_undecidable_left_out="", precision_undecidable_left_out_ci="",
    note="test set ends in July 2018, so coverage of vocabulary from later years is untested")])

# query_misses.csv: indexed test set sources not retrieved; development sources reached only by excluded terms
codes = read("reference_codes.csv")
pterms = collections.defaultdict(list)
for c in codes:
    if c["field"] == "Practice" and c["term"]:
        pterms[c["key"]].append(c["term"])
by_key = {s["key"]: s for s in src}
excluded = [t for t in regular if status.get((t["term"], t["type"])) == "excluded by yield"]
reach = collections.defaultdict(list)
for t in excluded:
    for k in runs[(t["term"], t["type"])]["hits"]:
        reach[k].append(t["term"])
miss = [s for s in idx_src if s["key"] not in cov] + [by_key[k] for k in sorted(set(reach) - f_hits)]
upsert("query_misses.csv", [dict(
    database=DB, doi=s["doi"], title=s["title"], set=s["set"], in_scope=s["in_scope"],
    sharing_reuse_terms="; ".join(pterms[s["key"]]), excluded_term="; ".join(reach.get(s["key"], [])))
    for s in miss])

# terms.csv: fill the step 3 columns for this database's sharing and reuse rows
by_form = {wf(t): (t["term"], t["type"]) for t in cand}
rows = read("terms.csv")
for r in rows:
    if r["database"] != DB or r["pcc_part"] not in ("sharing", "reuse"):
        continue
    k = by_form[syn[(r["term"], r["type"], DB)]]
    r["development_yield"] = runs[k]["y"]
    r["load_2015_2025"] = runs[k]["load"]
    r["sources_added"] = added_at_entry.get(k, "") if status.get(k) in ("in query", "fallback in query") else ""
    r["status"] = status.get(k, "excluded by yield")
write("terms.csv", rows)
print("final query:", final_q)
print("load", len(recs), "coverage", cov_all, "in scope", cov_in)

PYEOF
```

## 7. Query block: Web of Science

Runs plan step 3, method items 3 to 9 for Web of Science: term runs, yield threshold, draft, trim, index check, test set coverage and load. In `data/search_tests/`, it writes `query_runs_web-of-science.csv` and `load_web-of-science.csv`, replaces the Web of Science rows of `query_tests.csv` and `query_misses.csv`, and fills the step 3 columns of the Web of Science *sharing* and *reuse* rows in `terms.csv`. Expect one to several hours; each candidate costs one count, one load count and two or three identifier batches, and each draft round one query per remaining candidate.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 10h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/query_console_web-of-science.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "Web of Science"
# ---------- query block: plan step 3, method items 3 to 9 ----------
import collections
src = read("reference_sources.csv")
syn = {(r["term"], r["type"], r["database"]): r["written_form"] for r in read("term_syntax.csv")}
terms = read("terms.csv")
dev = [s for s in src if s["set"] == "development" and s["eligible_apart_from_year"] == "yes"]
test = [s for s in src if s["set"] == "test"]
log = []

cand = [t for t in terms if t["database"] == DB and t["pcc_part"] in ("sharing", "reuse")]
cand.sort(key=lambda t: t["type"] != "fallback")  # a fallback term keeps its status when another term writes the same string
seen, uniq = set(), []
for t in cand:
    k = syn[(t["term"], t["type"], DB)]
    if k not in seen:
        seen.add(k)
        uniq.append(t)
cand = uniq
fallback = [t for t in cand if t["type"] == "fallback"]
regular = [t for t in cand if t["type"] != "fallback"]


def wf(t):
    return syn[(t["term"], t["type"], DB)]


def q_of(ts):
    return " OR ".join(f"({wf(t)})" for t in ts)


DEV_SPAN = date_limit(DB, 2007, 2014)
REVIEW_SPAN = date_limit(DB, 2015, 2025)


def measure(ts):
    q = q_of(ts)
    recs = count(DB, f"({q}) AND {DEV_SPAN}")
    hits = retrieved(DB, q, dev)
    return q, recs, hits


# item 3: term runs
runs = {}
for t in cand:
    q, recs, hits = measure([t])
    load = count(DB, f"({q}) AND {REVIEW_SPAN}")
    y = round(1000 * len(hits) / recs, 3) if recs else 0
    runs[(t["term"], t["type"])] = dict(t=t, recs=recs, hits=hits, load=load, y=y)
    log.append(dict(step="term run", term=t["term"], type=t["type"], records_2007_2014=recs,
                    dev_sources=len(hits), yield_per_1000=y, load_2015_2025=load, keys=";".join(sorted(hits))))
    print("term run", t["term"], recs, len(hits), load, flush=True)

# item 4: threshold
q_all, recs_all, hits_all = measure(regular)
threshold = round(1000 * len(hits_all) / recs_all, 3) if recs_all else 0
log.append(dict(step="threshold", term="(all regular candidates)", type="", records_2007_2014=recs_all,
                dev_sources=len(hits_all), yield_per_1000=threshold, load_2015_2025="", keys=";".join(sorted(hits_all))))
print("threshold", threshold, flush=True)

# item 5: draft
status = {}
start = max(regular, key=lambda t: (len(runs[(t["term"], t["type"])]["hits"]), -runs[(t["term"], t["type"])]["recs"], t["term"]))
draft = [start]
added_at_entry = {(start["term"], start["type"]): len(runs[(start["term"], start["type"])]["hits"])}
_, d_recs, d_hits = measure(draft)
log.append(dict(step="draft start", term=start["term"], type=start["type"], records_2007_2014=d_recs,
                dev_sources=len(d_hits), yield_per_1000="", load_2015_2025="", keys=""))
rest = [t for t in regular if t is not start]
while rest:
    options = []
    for t in rest:
        r = runs[(t["term"], t["type"])]
        if not (r["hits"] - d_hits):
            continue
        _, recs, hits = measure(draft + [t])
        s_add, r_add = len(hits - d_hits), max(recs - d_recs, 0)
        y_add = 1000 * s_add / r_add if r_add else float("inf")
        options.append((-y_add, r_add, t["term"], t, recs, hits, s_add))
    options.sort(key=lambda o: (o[0], o[1], o[2]))
    best = None
    if options:
        o = options[0]
        best = (-o[0], None, None, o[3], o[4], o[5], o[6], o[1])
    if not best or best[0] < threshold:
        break
    y_add, _, _, t, recs, hits, s_add, r_add = best
    draft.append(t)
    added_at_entry[(t["term"], t["type"])] = s_add
    log.append(dict(step="draft add", term=t["term"], type=t["type"], records_2007_2014=recs,
                    dev_sources=len(hits), yield_per_1000=round(y_add, 3) if y_add != float("inf") else "inf",
                    load_2015_2025="", keys=f"added {s_add} sources for {r_add} records"))
    d_recs, d_hits = recs, hits
    rest = [x for x in rest if x is not t]
    print("added", t["term"], flush=True)
for t in rest:
    status[(t["term"], t["type"])] = "excluded by yield"
for t in fallback:
    draft.append(t)
    status[(t["term"], t["type"])] = "fallback in query"

# item 6: trim
for t in sorted([t for t in draft if t["type"] != "fallback"], key=lambda t: added_at_entry[(t["term"], t["type"])]):
    if len(draft) == 1:
        break
    trial = [x for x in draft if x is not t]
    hits = retrieved(DB, q_of(trial), dev)
    if hits == d_hits:
        draft = trial
        status[(t["term"], t["type"])] = "excluded by yield"
        log.append(dict(step="trim drop", term=t["term"], type=t["type"], records_2007_2014="", dev_sources=len(hits),
                        yield_per_1000="", load_2015_2025="", keys=""))
for t in draft:
    status.setdefault((t["term"], t["type"]), "in query")
final_q = q_of(draft)
_, f_recs, f_hits = measure(draft)

# items 7 and 8: index check and coverage on the test set
idx = set()
for i in range(0, len([s for s in test if testable(DB, s)]), BATCH):
    b = [s for s in test if testable(DB, s)][i:i + BATCH]
    clause = id_clause(DB, b)
    if DB == "PubMed":
        _, ids = pubmed_search(clause, retmax=BATCH * 2)
        idx |= {s["key"] for s in b if s["pmid"] in set(ids)}
        rest_b = [s for s in b if not s["pmid"]]
        if rest_b and ids:
            dois = {r["doi"] for r in pubmed_summary(ids).values()}
            idx |= {s["key"] for s in rest_b if s["doi"].lower() in dois}
    elif DB == "Scopus":
        dois = {r["doi"] for r in scopus_records(clause)}
        idx |= {s["key"] for s in b if s["doi"].lower() in dois}
    else:
        dois = {r["doi"] for r in wos_records(clause)}
        idx |= {s["key"] for s in b if s["doi"].lower() in dois}
untestable = [s["key"] for s in test if not testable(DB, s)]
idx_src = [s for s in test if s["key"] in idx]
cov = retrieved(DB, final_q, idx_src)
in_scope_idx = [s for s in idx_src if s["in_scope"] == "yes"]
cov_all = wilson(len(cov), len(idx_src))
cov_in = wilson(len([s for s in in_scope_idx if s["key"] in cov]), len(in_scope_idx))

# item 9: load
slug = {"PubMed": "pubmed", "Scopus": "scopus", "Web of Science": "web-of-science"}[DB]
load_q = f"({final_q}) AND {REVIEW_SPAN}"
recs = records(DB, load_q)
if DB == "PubMed":
    meta = pubmed_summary([r["id"] for r in recs])
    recs = [meta.get(r["id"], dict(id=r["id"], doi="", title="", year="")) for r in recs]
write(f"load_{slug}.csv", recs)
write(f"query_runs_{slug}.csv", log)


def upsert(name, rows):
    """Replace this database's rows in a file shared by the three databases."""
    old = [r for r in read(name) if r["database"] != DB] if (T / name).exists() and (T / name).stat().st_size else []
    write(name, old + rows)


upsert("query_tests.csv", [dict(
    database=DB, final_query=final_q, date_run=TODAY, yield_threshold=threshold,
    development_yield=round(1000 * len(f_hits) / f_recs, 3) if f_recs else 0, load=len(recs),
    test_indexed=len(idx_src), test_untestable=len(untestable), test_retrieved=len(cov),
    coverage_test=cov_all[0], coverage_test_ci=f"{cov_all[1]}-{cov_all[2]}",
    coverage_in_scope=cov_in[0], coverage_in_scope_ci=f"{cov_in[1]}-{cov_in[2]}",
    seed="", sample_included="", sample_excluded="", sample_undecidable="", sample_title_only="",
    precision_undecidable_included="", precision_undecidable_included_ci="",
    precision_undecidable_left_out="", precision_undecidable_left_out_ci="",
    note="test set ends in July 2018, so coverage of vocabulary from later years is untested")])

# query_misses.csv: indexed test set sources not retrieved; development sources reached only by excluded terms
codes = read("reference_codes.csv")
pterms = collections.defaultdict(list)
for c in codes:
    if c["field"] == "Practice" and c["term"]:
        pterms[c["key"]].append(c["term"])
by_key = {s["key"]: s for s in src}
excluded = [t for t in regular if status.get((t["term"], t["type"])) == "excluded by yield"]
reach = collections.defaultdict(list)
for t in excluded:
    for k in runs[(t["term"], t["type"])]["hits"]:
        reach[k].append(t["term"])
miss = [s for s in idx_src if s["key"] not in cov] + [by_key[k] for k in sorted(set(reach) - f_hits)]
upsert("query_misses.csv", [dict(
    database=DB, doi=s["doi"], title=s["title"], set=s["set"], in_scope=s["in_scope"],
    sharing_reuse_terms="; ".join(pterms[s["key"]]), excluded_term="; ".join(reach.get(s["key"], [])))
    for s in miss])

# terms.csv: fill the step 3 columns for this database's sharing and reuse rows
by_form = {wf(t): (t["term"], t["type"]) for t in cand}
rows = read("terms.csv")
for r in rows:
    if r["database"] != DB or r["pcc_part"] not in ("sharing", "reuse"):
        continue
    k = by_form[syn[(r["term"], r["type"], DB)]]
    r["development_yield"] = runs[k]["y"]
    r["load_2015_2025"] = runs[k]["load"]
    r["sources_added"] = added_at_entry.get(k, "") if status.get(k) in ("in query", "fallback in query") else ""
    r["status"] = status.get(k, "excluded by yield")
write("terms.csv", rows)
print("final query:", final_q)
print("load", len(recs), "coverage", cov_all, "in scope", cov_in)

PYEOF
```

## 8. Precision block: PubMed

Runs plan step 3, method item 10: draws 100 records from `load_pubmed.csv` with seed 20261112, fetches abstracts from PubMed for PubMed records, then from OpenAlex by DOI, then Crossref, records the seed in `query_tests.csv`, and writes `precision_sample_pubmed.csv` with empty `decision` and `exclusion_code` columns for screening. Records with no abstract are marked `none` in `abstract_source`.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 1h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/precision_console_pubmed.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "PubMed"
# ---------- precision block: plan step 3, method item 10 ----------
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

PYEOF
```

## 9. Precision block: Scopus

Runs plan step 3, method item 10: draws 100 records from `load_scopus.csv` with seed 20261112, fetches abstracts from PubMed for PubMed records, then from OpenAlex by DOI, then Crossref, records the seed in `query_tests.csv`, and writes `precision_sample_scopus.csv` with empty `decision` and `exclusion_code` columns for screening. Records with no abstract are marked `none` in `abstract_source`.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 1h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/precision_console_scopus.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "Scopus"
# ---------- precision block: plan step 3, method item 10 ----------
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

PYEOF
```

## 10. Precision block: Web of Science

Runs plan step 3, method item 10: draws 100 records from `load_web-of-science.csv` with seed 20261112, fetches abstracts from PubMed for PubMed records, then from OpenAlex by DOI, then Crossref, records the seed in `query_tests.csv`, and writes `precision_sample_web-of-science.csv` with empty `decision` and `exclusion_code` columns for screening. Records with no abstract are marked `none` in `abstract_source`.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
mkdir -p data/search_tests
timeout 1h python3 - 2>&1 <<'PYEOF' | tee data/search_tests/precision_console_web-of-science.txt
"""Search functions shared by the RDS-Review query and precision blocks.

Each block in server_blocks.md pastes this file's contents ahead of its own code,
so nothing needs installing beyond requests.
"""
import csv, json, os, random, re, time, datetime
from pathlib import Path
import requests

T = Path("data/search_tests")
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
    return list(csv.DictReader(open(T / name, encoding="utf-8")))


def write(name, rows, folder=T):
    folder.mkdir(parents=True, exist_ok=True)
    if not rows:
        (folder / name).write_text("")
        return
    with open(folder / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

DB = "Web of Science"
# ---------- precision block: plan step 3, method item 10 ----------
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

PYEOF
```

## 11. Reference set

Runs plan step 1, Reference set items 1 and 3. Reads the full text and reference list of Chawinga and Zinn (2019) through Elsevier's Article Retrieval API and selects the references the paper identifies as included sources: named in Table 2, cited in section 4 or 5, or supplying a country section 4.3 lists. Writes `reference_citations.csv` and `reference_candidates.csv` in `data/search_tests/`, and prints the reference set's size, types and years against the paper's own counts. Needs the Scopus key and McGill's network.

```bash
cd ~/RDS-Review
git pull
source ~/.venvs/rds-review/bin/activate
source ~/.rds-review-keys
timeout 600 python3 - <<'PYEOF'
# ---------- reference set block: plan step 1, Reference set item 1 ----------
import collections, csv, os, re, unicodedata
import xml.etree.ElementTree as ET
import requests

DOI = "10.1016/j.lisr.2019.04.004"
r = requests.get(f"https://api.elsevier.com/content/article/doi/{DOI}", params={"view": "FULL"},
                 headers={"X-ELS-APIKey": os.environ["SCOPUS_API_KEY"], "Accept": "text/xml"}, timeout=60)
r.raise_for_status()
root = ET.fromstring(r.content)
local = lambda t: t.rsplit("}", 1)[-1]
flat = lambda e: re.sub(r"\s+", " ", "".join(e.itertext())).strip() if e is not None else ""
fold = lambda s: unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
label_of = lambda e: flat(next((c for c in e if local(c.tag) == "label"), None))

# where each reference is cited: the label of the enclosing section, or of the table
where = collections.defaultdict(set)
sections = {}
def walk(e, section, table):
    tag = local(e.tag)
    if tag == "section":
        section = label_of(e) or section
        sections[section] = e
    if tag == "table":
        table = label_of(e) or table
    if tag in ("cross-ref", "cross-refs"):
        for rid in e.get("refid", "").split():
            if rid.startswith("bb"):
                where[rid].add(table or section)
    for c in e:
        walk(c, section, table)
walk(next(e for e in root.iter() if local(e.tag) == "body"), "", "")
table2 = fold(next(flat(t) for t in root.iter() if local(t.tag) == "table" and label_of(t) == "Table 2"))

# the reference list, with each reference's type read from its markup and title
rows = []
for b in root.iter():
    if local(b.tag) != "bib-reference":
        continue
    rid = b.get("id")
    find = lambda name: next((e for e in b.iter() if local(e.tag) == name), None)
    tags = {local(e.tag) for e in b.iter()}
    surnames = [flat(e) for e in b.iter() if local(e.tag) == "surname"]
    label = flat(find("label"))
    m = re.search(r"\d{4}", flat(find("date"))) or re.search(r"\d{4}", label)
    title = flat(find("maintitle"))
    words = fold(flat(b))
    if "issue" in tags or ("series" in tags and "book" not in tags):
        kind = "journal article"
    elif re.search(r"thesis|dissertation", words):
        kind = "thesis"
    elif "edited-book" in tags and "contribution" in tags:
        kind = "book chapter"
    elif "book" in tags or "edited-book" in tags:
        kind = "book"
    elif "report" in words:
        kind = "report"
    else:
        kind = "other"
    rows.append(dict(ref_id=rid, label=label, first_author=surnames[0] if surnames else label.split(",")[0],
                     year=m.group(0) if m else "", title=title, doi=flat(find("doi")).lower(), type=kind,
                     cited_in=";".join(sorted(where.get(rid, set())))))

# rule 1: named in Table 2, matched by first author and year; a year either way only where the
# reference list holds no reference by that author with Table 2's year
named = lambda name, year: re.search(re.escape(name) + r"[^()]{0,60}\(" + str(year) + r"\)", table2)
years_of = collections.defaultdict(set)
for x in rows:
    if x["year"].isdigit():
        years_of[fold(x["first_author"])].add(int(x["year"]))
for x in rows:
    name, y = fold(x["first_author"]), int(x["year"]) if x["year"].isdigit() else None
    hit = bool(name and y and named(name, y))
    if name and y and not hit:
        hit = any(named(name, y + d) and (y + d) not in years_of[name] for d in (-1, 1))
    x["in_table_2"] = "yes" if hit else "no"
# rule 2: cited in section 4 (Results) or section 5 (Discussion)
top = lambda x: {s.split(".")[0] for s in x["cited_in"].split(";") if s}
for x in rows:
    basis = []
    if x["in_table_2"] == "yes":
        basis.append("Table 2")
    if top(x) & {"4", "5"}:
        basis.append("section 4 or 5")
    x["basis"] = "; ".join(basis)
# rule 3: section 4.3 lists the countries with one included publication each; a country no
# selected reference names in its title is supplied by the reference whose title names it
s43 = fold(flat(sections["4.3"]))
countries = [c.strip() for c in re.search(r"other category include (.+?)\.", s43).group(1).replace(" and ", ", ").split(",") if c.strip()]
chosen = [x for x in rows if x["basis"]]
for c in sorted(set(countries)):
    if any(c in fold(x["title"]) for x in chosen):
        continue
    for x in rows:
        if not x["basis"] and c in fold(x["title"]) and x["year"].isdigit() and 2007 <= int(x["year"]) <= 2018:
            x["basis"] = f"section 4.3 country: {c}"
for x in rows:
    x["in_reference_set"] = "yes" if x["basis"] else "no"

def write(name, data):
    with open(f"data/search_tests/{name}", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(data)
write("reference_citations.csv", rows)
ref_set = [x for x in rows if x["in_reference_set"] == "yes"]
write("reference_candidates.csv", ref_set)

# checks against the paper's own figures
print(f"{len(rows)} references; reference set {len(ref_set)} (paper: 105)")
print("by basis:", dict(collections.Counter(x["basis"] for x in ref_set)))
print("by type:", dict(collections.Counter(x["type"] for x in ref_set)), "(paper: 83 journal articles, 10 theses, 8 reports, 4 books)")
fig4 = {2007: 3, 2008: 3, 2009: 11, 2010: 6, 2011: 7, 2012: 14, 2013: 14, 2014: 6, 2015: 11, 2016: 9, 2017: 12, 2018: 9}
have = collections.Counter(int(x["year"]) for x in ref_set if x["year"].isdigit())
print("by year (set / Fig. 4):", {y: f"{have.get(y, 0)}/{n}" for y, n in fig4.items()})
print("section 4.3 countries:", countries)
print("added by section 4.3:", [(x["first_author"], x["year"]) for x in ref_set if x["basis"].startswith("section 4.3")])

PYEOF
```
