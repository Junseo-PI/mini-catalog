from dotenv import load_dotenv
from openai import OpenAI
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "catalog", "rules.txt")
PROFILES = os.path.join(ROOT, "output", "profiles.json")
SOURCES = os.path.join(ROOT, "data", "SOURCES.md")
CATALOG = os.path.join(ROOT, "output", "catalog.json")

MODEL = "gpt-4o"


def load_profiles():
    try:
        with open(PROFILES, "r") as f:
            profiles = json.load(f)

    except Exception as e:
        print(f"Failed to load profiles: {e}")
        return []

    return profiles


def load_rules():
    with open(RULES, "r") as f:
        return f.read()


def load_titles():
    """Map each table name to its dataset title from SOURCES.md."""
    titles = {}
    current_tables = []
    with open(SOURCES, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("### "):
                files = line[len("### "):].split(",")
                current_tables = [os.path.splitext(name.strip())[0] for name in files]
            elif line.startswith("- Title:"):
                title = line[len("- Title:"):].strip()
                for table in current_tables:
                    titles[table] = title
    return titles


def build_prompt(profile, title=None):
    cols = []
    for col in profile["columns"]:
        cols.append({
            "name": col["name"],
            "dtype": col.get("dtype", "unknown"),
            "samples": col.get("samples", []),
        })

    input_profile = {"table_name": profile["table_name"]}
    if title:
        input_profile["dataset_title"] = title
    input_profile["n_rows"] = profile["n_rows"]
    input_profile["n_cols"] = profile["n_cols"]
    input_profile["columns"] = cols

    return "Table profile (JSON):\n" + json.dumps(input_profile, indent=2)


def enrich_table(client, profile, title=None):
    response = client.responses.create(
        model=MODEL,
        instructions=load_rules(),
        input=build_prompt(profile, title),
        text={"format": {"type": "json_object"}},
        temperature=0,
    )
    result = json.loads(response.output_text)

    return result


def load_catalog():
    """Return cached results as {table_name: result}, or {} if none yet."""
    if not os.path.exists(CATALOG):
        return {}

    with open(CATALOG, "r") as f:
        entries = json.load(f)

    catalog = {}
    for entry in entries:
        catalog[entry["table_name"]] = entry
    return catalog


def save_catalog(catalog):
    entries = list(catalog.values())

    with open(CATALOG, "w") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def check_result(profile, result):
    """Return True if the LLM result covers exactly the profile's columns."""
    if not result.get("description") or not result.get("tags"):
        return False

    profile_names = [col["name"] for col in profile["columns"]]
    result_names = [col.get("name") for col in result.get("columns", [])]
    return profile_names == result_names


def main():
    load_dotenv()
    client = OpenAI()

    profiles = load_profiles()
    titles = load_titles()
    catalog = load_catalog()

    new = 0
    cached = 0
    failed = 0

    for profile in profiles:
        name = profile["table_name"]

        if name in catalog:
            print(f"Cached {name}")
            cached += 1
            continue

        try:
            result = enrich_table(client, profile, titles.get(name))
        except Exception as e:
            print(f"Skipped {name}: {e}")
            failed += 1
            continue

        if not check_result(profile, result):
            print(f"Skipped {name}: result does not match the profile")
            failed += 1
            continue

        catalog[name] = result
        save_catalog(catalog)
        print(f"Enriched {name}: {profile['n_rows']} rows, {profile['n_cols']} cols")
        new += 1

    print(f"Done: {new} new, {cached} cached, {failed} failed")


if __name__ == "__main__":
    main()
