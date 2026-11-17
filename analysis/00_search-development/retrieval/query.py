"""Step 3 query for one database, method items 3 to 9: term runs, yield threshold, draft, trim, index check, test set coverage and load."""
import sys
from search_lib import *
from search_lib import _get

if len(sys.argv) != 2 or sys.argv[1] not in DATABASES:
    sys.exit("give one database: " + ", ".join(DATABASES))
DB = DATABASES[sys.argv[1]]
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
        idx |= {s["ref_id"] for s in b if s["pmid"] in set(ids)}
        rest_b = [s for s in b if not s["pmid"]]
        if rest_b and ids:
            dois = {r["doi"] for r in pubmed_summary(ids).values()}
            idx |= {s["ref_id"] for s in rest_b if s["doi"].lower() in dois}
    elif DB == "Scopus":
        dois = {r["doi"] for r in scopus_records(clause)}
        idx |= {s["ref_id"] for s in b if s["doi"].lower() in dois}
    else:
        dois = {r["doi"] for r in wos_records(clause)}
        idx |= {s["ref_id"] for s in b if s["doi"].lower() in dois}
untestable = [s["ref_id"] for s in test if not testable(DB, s)]
idx_src = [s for s in test if s["ref_id"] in idx]
cov = retrieved(DB, final_q, idx_src)
in_scope_idx = [s for s in idx_src if s["in_scope"] == "yes"]
elig_idx = [s for s in idx_src if s["eligible_apart_from_year"] == "yes"]
cov_all = wilson(len(cov), len(idx_src))
cov_in = wilson(len([s for s in in_scope_idx if s["ref_id"] in cov]), len(in_scope_idx))
cov_el = wilson(len([s for s in elig_idx if s["ref_id"] in cov]), len(elig_idx))

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
    old = [r for r in read(name) if r["database"] != DB] if path(name).exists() and path(name).stat().st_size else []
    write(name, old + rows)


upsert("query_tests.csv", [dict(
    database=DB, final_query=final_q, date_run=TODAY, yield_threshold=threshold,
    development_yield=round(1000 * len(f_hits) / f_recs, 3) if f_recs else 0, load=len(recs),
    test_indexed=len(idx_src), test_untestable=len(untestable), test_retrieved=len(cov),
    coverage_test=cov_all[0], coverage_test_ci=f"{cov_all[1]}-{cov_all[2]}",
    coverage_eligible=cov_el[0], coverage_eligible_ci=f"{cov_el[1]}-{cov_el[2]}",
    coverage_in_scope=cov_in[0], coverage_in_scope_ci=f"{cov_in[1]}-{cov_in[2]}",
    seed="", sample_included="", sample_excluded="", sample_undecidable="", sample_title_only="",
    precision_undecidable_included="", precision_undecidable_included_ci="",
    precision_undecidable_left_out="", precision_undecidable_left_out_ci="",
    note="test set ends in 2018, so coverage of vocabulary from later years is untested")])

# query_misses.csv: indexed test set sources not retrieved; development sources reached only by excluded terms
codes = read(CODES)
pterms = collections.defaultdict(list)
for c in codes:
    if c["field"] == "practice" and c["term"] not in ("", "none"):
        pterms[c["ref_id"]].append(c["term"])
by_key = {s["ref_id"]: s for s in src}
excluded = [t for t in regular if status.get((t["term"], t["type"])) == "excluded by yield"]
reach = collections.defaultdict(list)
for t in excluded:
    for k in runs[(t["term"], t["type"])]["hits"]:
        reach[k].append(t["term"])
miss = [s for s in idx_src if s["ref_id"] not in cov] + [by_key[k] for k in sorted(set(reach) - f_hits)]
upsert("query_misses.csv", [dict(
    database=DB, ref_id=s["ref_id"], doi=s["doi"], title=s["title"], set=s["set"],
    eligible_apart_from_year=s["eligible_apart_from_year"], in_scope=s["in_scope"],
    sharing_reuse_terms="; ".join(pterms[s["ref_id"]]), excluded_term="; ".join(reach.get(s["ref_id"], [])))
    for s in miss])

# term_results.csv: the step 3 results for this database's sharing and reuse terms; terms that write the
# same search string share one result
by_form = {wf(t): (t["term"], t["type"]) for t in cand}
results = []
for r in terms:
    if r["database"] != DB or r["pcc_part"] not in ("sharing", "reuse"):
        continue
    k = by_form[syn[(r["term"], r["type"], DB)]]
    results.append(dict(database=DB, term=r["term"], type=r["type"], pcc_part=r["pcc_part"],
                        written_form=syn[(r["term"], r["type"], DB)], development_yield=runs[k]["y"],
                        load_2015_2025=runs[k]["load"],
                        sources_added=added_at_entry.get(k, "") if status.get(k) in ("in query", "fallback in query") else "",
                        status=status.get(k, "excluded by yield")))
upsert("term_results.csv", results)
print("final query:", final_q)
print("load", len(recs), "coverage", cov_all, "eligible", cov_el, "in scope", cov_in)
