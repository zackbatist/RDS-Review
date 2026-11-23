"""Terms the known sources use: sends each reference set source's title and abstract to the local model with
prompts/terms_prompt.md and writes one row per term to a file named after the model, with where the term appears.

The model runs on a llama.cpp server that scripts/launch_rds_llm.sh starts. LLM_URL names the server, by default
http://localhost:11450. The argument names the output file in data/raw/search-development/, such as
terms_qwen3.8-27b.csv. The input is reference_lookups.csv. Temperature and seed are those of coding.py.
"""
import csv, datetime, json, os, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "search-development"
PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "terms_prompt.md").read_text(encoding="utf-8").rstrip("\n")
URL = os.environ.get("LLM_URL", "http://localhost:11450").rstrip("/")
if len(sys.argv) != 2:
    sys.exit("give the output file name, such as terms_qwen3.8-27b.csv")
OUT = RAW / sys.argv[1]
TEMPERATURE, SEED, MAX_TOKENS = 0, 20261116, 2048

# the answer must be a list of terms
SCHEMA = {"type": "object", "properties": {"terms": {"type": "array", "items": {"type": "string"}}},
          "required": ["terms"], "additionalProperties": False}


def call(path, body=None):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


def squash(s):
    """Lowercase letters and digits only, so spacing, hyphens and punctuation don't count."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def where(term, title, abstract):
    """Whether the term appears in the title, the abstract, both, or neither."""
    t = squash(term)
    places = [name for name, text in (("title", title), ("abstract", abstract)) if t and t in squash(text)]
    return " and ".join(places) or "not in text"


props = call("/props")
run = dict(model=Path(props.get("model_path", "")).name, build=props.get("build_info", ""),
           temperature=TEMPERATURE, seed=SEED, run_date=datetime.date.today().isoformat())
print(f"model {run['model']}, build {run['build']}; writing {OUT}", flush=True)

refs = list(csv.DictReader(open(RAW / "reference_lookups.csv", encoding="utf-8")))
rows = []
for i, x in enumerate(refs, 1):
    title, abstract = x["title"], x["abstract"].strip()
    coded_on = "title and abstract" if abstract else "title only"
    prompt = PROMPT.replace("{title}", title).replace("{abstract}", abstract or "none")
    body = dict(messages=[{"role": "user", "content": prompt}], temperature=TEMPERATURE, seed=SEED,
                max_tokens=MAX_TOKENS, cache_prompt=False, chat_template_kwargs={"enable_thinking": False},
                response_format={"type": "json_schema", "json_schema": {"name": "terms", "schema": SCHEMA}})
    reply = call("/v1/chat/completions", body)["choices"][0]["message"]["content"]
    try:
        terms = json.loads(reply)["terms"]
    except (json.JSONDecodeError, KeyError):
        terms = []
        print(f"{i:>3} {x['ref_id']}: reply is not usable JSON: {reply[:200]}", flush=True)
    for t in terms:
        rows.append(dict(ref_id=x["ref_id"], doi=x["doi"], coded_on=coded_on, term=t,
                         location=where(t, title, abstract), **run))
    missing = sum(1 for t in terms if where(t, title, abstract) == "not in text")
    print(f"{i:>3} {x['first_author']} {x['year_cited']}: {coded_on}, {len(terms)} terms, {missing} not in text", flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ref_id", "doi", "coded_on", "term", "location", *run], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

print(f"\nsources: {len(refs)}; terms: {len(rows)}; not in text: {sum(1 for r in rows if r['location'] == 'not in text')}")
print("sources with no terms:", sum(1 for x in refs if not any(r["ref_id"] == x["ref_id"] for r in rows)))
