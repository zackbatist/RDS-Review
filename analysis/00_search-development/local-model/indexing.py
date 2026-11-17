"""Step 2 assignment: sends each distinct indexing term in reference_indexing.csv to the local model with prompts/indexing_prompt.md, one term at a time, and writes the value it gives each term to a file of assignments named after the model.

The model runs on a llama.cpp server that scripts/launch_rds_llm.sh starts. LLM_URL names the server, by default http://localhost:11450.
The argument names the output file in data/raw/search-development/, after the model: term_assignments_<model>.csv.
"""
import csv, datetime, json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "search-development"
PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "indexing_prompt.md").read_text(encoding="utf-8")
URL = os.environ.get("LLM_URL", "http://localhost:11450").rstrip("/")
if len(sys.argv) != 2:
    sys.exit("give the output file name, such as term_assignments_qwen3.5-122b.csv")
OUT = RAW / sys.argv[1]
TEMPERATURE, SEED, MAX_TOKENS = 0, 20261116, 64

# The values in prompts/indexing_prompt.md: the two practices, each factor with its theme, and none.
THEMES = {
    "factors that obstruct": ["barriers", "challenges", "obstacles", "reluctance", "privacy"],
    "factors that facilitate": ["facilitators", "enablers", "incentives", "motivation", "infrastructure",
                                "repositories", "interoperability"],
    "stakeholder perspectives": ["perceptions", "attitudes", "willingness"],
    "policies and what drive them": ["policies", "mandates", "open science", "open data", "open access",
                                     "open research"],
    "mechanisms for implementation": ["governance", "consent", "licensing", "ethics", "stewardship",
                                      "data management plans", "data curation", "digital curation"],
}
THEME_OF = {v: t for t, vs in THEMES.items() for v in vs}
VALUES = ["sharing", "reuse"] + list(THEME_OF) + ["none"]
SCHEMA = {"type": "object", "properties": {"value": {"enum": VALUES}}, "required": ["value"],
          "additionalProperties": False}


def call(path, body=None):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


props = call("/props")
run = dict(model=Path(props.get("model_path", "")).name, build=props.get("build_info", ""),
           temperature=TEMPERATURE, seed=SEED, run_date=datetime.date.today().isoformat())
print(f"model {run['model']}, build {run['build']}; writing {OUT.name}", flush=True)

# one row per distinct term and type, in a fixed order
terms = {}
for i in csv.DictReader(open(RAW / "reference_indexing.csv", encoding="utf-8")):
    if i["term"].strip():
        terms[(i["type"], i["term"])] = i["scope_note"]
terms = sorted(terms.items(), key=lambda x: (x[0][0], x[0][1].lower()))

rows = []
for n, ((kind, term), note) in enumerate(terms, 1):
    shown = f"{term} ({kind})" + (f". Scope note: {note}" if kind == "MeSH" and note else "")
    body = dict(messages=[{"role": "user", "content": PROMPT.replace("{term}", shown)}],
                temperature=TEMPERATURE, seed=SEED, max_tokens=MAX_TOKENS, cache_prompt=False,
                response_format={"type": "json_schema", "json_schema": {"name": "value", "schema": SCHEMA}},
                chat_template_kwargs={"enable_thinking": False})
    reply = call("/v1/chat/completions", body)["choices"][0]["message"]["content"]
    try:
        value, problem = json.loads(reply)["value"], ""
    except (json.JSONDecodeError, KeyError, TypeError):
        value, problem = "", "reply is not the expected JSON: " + reply[:200]
    rows.append(dict(type=kind, term=term, scope_note=note, value=value,
                     theme=THEME_OF.get(value, ""), problem=problem, **run))
    print(f"{n}/{len(terms)} {kind}: {term} -> {value or problem}", flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

count = lambda key: dict(sorted(((v, sum(1 for r in rows if r[key] == v)) for v in {r[key] for r in rows}),
                                key=lambda x: -x[1]))
print(f"\nterms: {len(rows)}; with a problem: {sum(1 for r in rows if r['problem'])}")
print("by value:", count("value"))
print("by theme:", count("theme"))
