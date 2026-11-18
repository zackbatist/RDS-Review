"""Scope sample screening: sends each record of scope_sample_records.csv to the local model with prompts/scope_prompt.md,
the screening guide's criteria without the tier criterion, and writes one row per record to a file named after the model.

The model runs on a llama.cpp server that scripts/launch_rds_llm.sh starts. LLM_URL names the server, by default
http://localhost:11450. The argument names the output file in data/raw/search-development/, such as
scope_screening_qwen3.5-122b.csv. The settings are those of coding.py.
"""
import csv, datetime, json, os, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "search-development"
PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "scope_prompt.md").read_text(encoding="utf-8")
URL = os.environ.get("LLM_URL", "http://localhost:11450").rstrip("/")
if len(sys.argv) != 2:
    sys.exit("give the output file name, such as scope_screening_qwen3.5-122b.csv")
OUT = RAW / sys.argv[1]
TEMPERATURE, SEED, MAX_TOKENS = 0, 20261116, 1024

# the answer must use the prompt's values
SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"enum": ["include", "exclude", "undecidable"]},
        "exclusion_code": {"enum": ["not-data-sharing", "not-factors", "not-research-data", "system-design",
                                    "language", "none"]},
        "field": {"enum": ["health", "other", "cross-disciplinary"]},
        "review": {"enum": ["yes", "no"]},
        "reason": {"type": "string"},
    },
    "required": ["decision", "exclusion_code", "field", "review", "reason"],
    "additionalProperties": False,
}


def call(path, body=None):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)


props = call("/props")
run = dict(model=Path(props.get("model_path", "")).name, build=props.get("build_info", ""),
           temperature=TEMPERATURE, seed=SEED, run_date=datetime.date.today().isoformat())
print(f"model {run['model']}, build {run['build']}; writing {OUT.name}", flush=True)

rows = []
for x in csv.DictReader(open(RAW / "scope_sample_records.csv", encoding="utf-8")):
    abstract = x["abstract"].strip()
    prompt = PROMPT.replace("{title}", x["title"]).replace("{abstract}", abstract or "none")
    body = dict(messages=[{"role": "user", "content": prompt}], temperature=TEMPERATURE, seed=SEED,
                max_tokens=MAX_TOKENS, cache_prompt=False, chat_template_kwargs={"enable_thinking": False},
                response_format={"type": "json_schema", "json_schema": {"name": "screening", "schema": SCHEMA}})
    reply = call("/v1/chat/completions", body)["choices"][0]["message"]["content"]
    row = dict(order=x["order"], record_id=x["record_id"], database=x["database"], doi=x["doi"], title=x["title"],
               year=x["year"], judged_on="title and abstract" if abstract else "title only",
               decision="", exclusion_code="", field="", review="", reason="", problem="")
    try:
        a = json.loads(reply)
        row.update({k: a.get(k, "") for k in ("decision", "exclusion_code", "field", "review", "reason")})
        if a.get("decision") == "exclude" and a.get("exclusion_code") == "none":
            row["problem"] = "excluded with no code"
    except json.JSONDecodeError:
        row["problem"] = "reply is not JSON: " + reply[:200]
    rows.append(dict(row, **run))
    print(f"{x['order']:>3} {x['record_id']}: {row['decision'] or row['problem']}", flush=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

done = [r for r in rows if r["decision"]]
print(f"\n{len(rows)} records; {len(done)} judged; problems: {sum(1 for r in rows if r['problem'])}")
