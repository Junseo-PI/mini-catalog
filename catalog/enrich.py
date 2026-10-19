from dotenv import load_dotenv
from openai import OpenAI
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "catalog", "rules.txt")
PROFILES = os.path.join(ROOT, "output", "profiles.json")
SOURCES = os.path.join(ROOT, "data", "SOURCES.md")

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
            "dtype": col["dtype"],
            "samples": col["samples"],
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
    output_profile = json.loads(response.output_text)

    return output_profile


if __name__ == "__main__":
    load_dotenv()
    client = OpenAI()

    profiles = load_profiles()
    titles = load_titles()
    profile = [p for p in profiles if p["table_name"] == "nwlr_survey1"][0]
    title = titles.get(profile["table_name"])

    # print(build_prompt(profile, title))
    result = enrich_table(client, profile, title)
    print(json.dumps(result, indent=2))
