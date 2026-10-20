import streamlit as st
from catalog.search import load_catalog, build_index, search
import os
import json
import pandas as pd


ROOT = os.path.dirname(os.path.abspath(__file__))
PROFILES = os.path.join(ROOT, "output", "profiles.json")


def load_profiles():
    try:
        with open(PROFILES, "r") as f:
            profiles = json.load(f)

    except Exception as e:
        print(f"Failed to load profiles: {e}")
        return []

    return profiles


@st.cache_data
def get_catalog():
    return load_catalog()


@st.cache_data
def get_profiles():
    """Return profiles as {table_name: profile} for quick lookup."""
    profiles = {}
    for profile in load_profiles():
        profiles[profile["table_name"]] = profile
    return profiles


@st.cache_resource
def get_index(use_enrichment):
    print(f"Building index (use_enrichment={use_enrichment})")
    return build_index(get_catalog(), use_enrichment=use_enrichment)


def show_columns(entry, profile):
    """Show a collapsible table joining LLM expansions with profile stats."""
    stats = {}
    if profile:
        stats = {col["name"]: col for col in profile["columns"]}

    rows = []
    for col in entry["columns"]:
        stat = stats.get(col["name"], {})
        rows.append({
            "Column": col["name"],
            "Expanded": col["expanded"],
            "Type": stat.get("dtype", ""),
            "Missing": f"{stat.get('null_ratio', 0):.0%}",
            "Samples": ", ".join(stat.get("samples", [])),
        })

    label = f"Columns ({len(rows)})"
    if profile:
        label += f" · {profile['n_rows']:,} rows"
    with st.expander(label):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def main():
    st.title("Mini Catalog Search")
    st.write("Search for datasets in the catalog.")

    catalog = get_catalog()
    profiles = get_profiles()
    enriched_index = get_index(True)
    plain_index = get_index(False)

    st.caption(f"Loaded {len(catalog)} tables ({len(profiles)} profiles).")

    query = st.text_input("Search", placeholder="e.g. gross primary production")
    use_enrichment = st.toggle("Use AI enrichment", value=True)
    if use_enrichment:
        st.caption("Searching table names, column names, expanded names, descriptions, and tags.")
    else:
        st.caption("Searching only the original table and column names.")

    if not query:
        st.info("Type a few words to search the catalog.")
        return

    index = enriched_index if use_enrichment else plain_index
    results = search(index, catalog, query, k=5)
    if not results:
        st.warning(f"No tables matched \"{query}\".")
        return

    entries = {entry["table_name"]: entry for entry in catalog}
    for table_name, score in results:
        entry = entries[table_name]
        st.subheader(table_name)
        st.caption(f"Score {score}")
        st.write(entry["description"])
        st.markdown(" ".join(f"`{tag}`" for tag in entry["tags"]))
        show_columns(entry, profiles.get(table_name))
        st.divider()


if __name__ == "__main__":
    main()
