"""Step 1 reference set, items 1 and 3: reads the full text of Chawinga and Zinn (2019) from Elsevier, selects the references the paper identifies as included sources, and checks the set against the paper's counts."""
import collections, csv, os, re, unicodedata
import xml.etree.ElementTree as ET
import requests
from search_lib import path

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
    with open(path(name), "w", newline="", encoding="utf-8") as f:
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
