"""Step 1 coding: sends each reference set source's title and abstract to the local model with prompts/coding_prompt.md and writes one row per coded value to reference_codes.csv.

The model runs on a llama.cpp server that scripts/launch_rds_llm.sh starts. LLM_URL names the server, by default http://localhost:11450.
An optional argument names the output file in data/raw/search-development/, by default reference_codes.csv.
"""
import csv, datetime, difflib, json, os, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "search-development"
PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "coding_prompt.md").read_text(encoding="utf-8")
URL = os.environ.get("LLM_URL", "http://localhost:11450").rstrip("/")
OUT = RAW / (sys.argv[1] if len(sys.argv) > 1 else "reference_codes.csv")
TEMPERATURE, SEED, MAX_TOKENS = 0, 20261116, 4096

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
VALUES = {
    "practice": ["sharing", "reuse", "both", "neither"],
    "data_origin": ["research", "not-research-data", "reused", "mixed", "unclear"],
    "field": ["health", "other", "cross-disciplinary"],
    "source_type": ["empirical", "review", "policy-guidance", "opinion", "other"],
    "language": ["English", "French", "other"],
}


def call(path, body=None):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


def squash(s):
    """Lowercase letters and digits only, so spacing, punctuation and quote marks don't count."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def found(part, text):
    """Whether part appears in text: exactly once squashed, or with at least 95% of its characters
    matching in order around the place its longest matching stretch puts it, which allows for
    abstracts with split words or a lost first letter."""
    p, t = squash(part), squash(text)
    if not p or p in t:
        return True
    blocks = [b for b in difflib.SequenceMatcher(None, t, p, autojunk=False).get_matching_blocks() if b.size]
    if not blocks:
        return False
    main = max(blocks, key=lambda b: b.size)
    start = main.a - main.b
    near = [b for b in blocks if start - 0.1 * len(p) <= b.a <= start + 1.1 * len(p)]
    return sum(b.size for b in near) >= 0.95 * len(p)


def problems(field, code, text):
    """What is wrong with one code: a passage or term not in the source's title and abstract."""
    out = []
    for key in ("passage", "term"):
        s = code.get(key, "none")
        if s != "none" and not found(s, text):
            out.append(f"{key} not found in the title or abstract")
    return "; ".join(out)


def code_schema(values, theme=None):
    props = {"value": {"enum": values}}
    if theme is not None:
        props["theme"] = {"const": theme}
    props.update(passage={"type": "string"}, term={"type": "string"},
                 location={"enum": ["title", "abstract", "none"]})
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


# The answer must follow this schema: every value is one the prompt defines, and every factor pairs
# a theme with one of that theme's entries, or is the single code "none".
SCHEMA = {
    "type": "object",
    "properties": {
        "practice": code_schema(VALUES["practice"]),
        "data_origin": code_schema(VALUES["data_origin"]),
        "factors": {"type": "array", "minItems": 1, "items": {"anyOf": [
            code_schema(entries, theme) for theme, entries in THEMES.items()] + [code_schema(["none"], "none")]}},
        "field": code_schema(VALUES["field"]),
        "source_type": code_schema(VALUES["source_type"]),
        "language": {"enum": VALUES["language"]},
    },
    "required": ["practice", "data_origin", "factors", "field", "source_type", "language"],
    "additionalProperties": False,
}


props = call("/props")
model = Path(props.get("model_path", "")).name
build = props.get("build_info", "")
n_ctx = props.get("default_generation_settings", {}).get("n_ctx", "")
print(f"model {model}, build {build}, context {n_ctx}; writing {OUT.name}", flush=True)
run = dict(model=model, build=build, temperature=TEMPERATURE, seed=SEED,
           run_date=datetime.date.today().isoformat())



def save():
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


refs = list(csv.DictReader(open(RAW / "reference_lookups.csv", encoding="utf-8")))
rows = []
for x in refs:
    abstract = x["abstract"].strip()
    coded_on = "title and abstract" if abstract else "title only"
    prompt = PROMPT.replace("{title}", x["title"]).replace("{abstract}", abstract or "none")
    body = dict(messages=[{"role": "user", "content": prompt}], temperature=TEMPERATURE, seed=SEED,
                max_tokens=MAX_TOKENS, response_format={"type": "json_schema", "json_schema": {"name": "codes", "schema": SCHEMA}}, cache_prompt=False,
                chat_template_kwargs={"enable_thinking": False})
    reply = call("/v1/chat/completions", body)["choices"][0]["message"]["content"]
    base = dict(ref_id=x["ref_id"], doi=x["doi"], coded_on=coded_on)
    try:
        answer = json.loads(reply)
    except json.JSONDecodeError:
        rows.append(dict(base, field="", value="", theme="", term="", location="", passage="",
                         problem="reply is not JSON: " + reply[:200], **run))
        print(f"{x['first_author']} {x['year_cited']}: reply is not JSON", flush=True)
        save()
        continue
    text = x["title"] + " " + abstract
    for field in ("practice", "data_origin", "factors", "field", "source_type", "language"):
        got = answer.get(field)
        codes = got if isinstance(got, list) else [got]
        if field == "language":
            codes = [{"value": got, "passage": "none", "term": "none", "location": "none"}]
        for c in codes:
            c = c if isinstance(c, dict) else {}
            p = problems(field, c, text)
            rows.append(dict(base, field=field, value=c.get("value", ""), theme=c.get("theme", ""),
                             term=c.get("term", ""), location=c.get("location", ""),
                             passage=c.get("passage", ""), problem=p, **run))
    flagged = sum(1 for r in rows if r["ref_id"] == x["ref_id"] and r["problem"])
    print(f"{x['first_author']} {x['year_cited']}: {coded_on}, {flagged} problem(s)", flush=True)
    save()

print(f"\nsources: {len(refs)}; codes: {len(rows)}; codes with a problem: {sum(1 for r in rows if r['problem'])}")
print("coded on title only:", len({r['ref_id'] for r in rows if r['coded_on'] == 'title only'}))
