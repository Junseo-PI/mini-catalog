import json
import os
import re
from rank_bm25 import BM25Okapi


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "output", "catalog.json")


def load_catalog():
    try:
        with open(CATALOG, "r") as f:
            catalog = json.load(f)

    except Exception as e:
        print(f"Failed to load catalog: {e}")
        return []

    return catalog


def tokenize(text):
    # Split camelCase and digit-letter boundaries before lowercasing:
    # "lakeName" -> "lake Name", "mgO2L" -> "mg O2 L"
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", text)
    text = text.lower()
    tokens = re.findall(r"[a-z0-9]+", text)

    return tokens


def build_document(entry, use_enrichment=True):
    string = ""

    string += entry["table_name"] + " "

    for col in entry["columns"]:
        string += col["name"] + " "

    if use_enrichment:
        if "description" in entry:
            string += entry["description"] + " "

        if "tags" in entry:
            string += " ".join(entry["tags"]) + " "

        for col in entry["columns"]:
            if "expanded" in col:
                string += col["expanded"] + " "

    return string


def build_index(entries, use_enrichment=True):
    documents = [build_document(entry, use_enrichment) for entry in entries]
    tokenized_documents = [tokenize(doc) for doc in documents]

    return BM25Okapi(tokenized_documents)


def search(index, entries, query, k=3):
    tokenized_query = tokenize(query)
    scores = index.get_scores(tokenized_query)

    matched = [i for i in range(len(scores)) if scores[i] > 0]
    top_indices = sorted(matched, key=lambda i: scores[i], reverse=True)[:k]

    results = []
    for i in top_indices:
        results.append((entries[i]["table_name"], round(float(scores[i]), 2)))
    return results


def main():
    catalog = load_catalog()

    queries = [
        "gross primary production",
        "lake name",
        "mg O2 L",
        "chlorophyll a",
        "dissolved organic carbon",
        "total nitrogen",
        "total phosphorus",
        "invasive species"
    ]

    for query in queries:
        print(f"Query: {query}")
        print("    with enrichment: ", search(build_index(catalog), catalog, query))
        print("    without enrichment: ", search(build_index(catalog, False), catalog, query))
        print()


if __name__ == "__main__":
    main()