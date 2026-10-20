"""Make a Columbo dataset from a subset of EDI_demo tables.

Run with Columbo's .venv:
    python make_subset.py EDI_mini                 # the 3-table smoke test
    python make_subset.py EDI_main --tables 20     # random tables for the main evaluation
"""
import argparse
import json
import os

import pandas as pd

COLUMBO = os.path.expanduser("~/github/columbo/clean_data")
HERE = os.path.dirname(os.path.abspath(__file__))

SMOKE_TEST_TABLES = [
    "APT022.csv",
    "mcmlter-clim-hodm_radn-monthly-20230706.csv",
    "HODM_ICET_MONTHLY.csv",
]
MIN_LABELED, MAX_LABELED = 5, 40


def pick_random_tables(gold, n, seed):
    """Pick n tables with 5-40 labeled columns, at most one per data package."""
    labeled = gold[gold["gt_label"].notna() & (gold["gt_label"] != "")]
    sizes = labeled.groupby("table_name").size()
    candidates = sizes[(sizes >= MIN_LABELED) & (sizes <= MAX_LABELED)].index
    candidates = candidates.difference(SMOKE_TEST_TABLES)

    tables = gold[gold["table_name"].isin(candidates)][["package_id", "table_name"]].drop_duplicates()
    one_per_package = tables.groupby("package_id").sample(n=1, random_state=seed)
    return sorted(one_per_package.sample(n=n, random_state=seed)["table_name"])


def main(args):
    gold = pd.read_pickle(os.path.join(COLUMBO, "EDI_demo", "gold.pkl"))
    if args.tables:
        tables = pick_random_tables(gold, args.tables, args.seed)
    else:
        tables = SMOKE_TEST_TABLES

    subset = gold[gold["table_name"].isin(tables)].reset_index(drop=True)
    out = os.path.join(COLUMBO, args.dataset)
    os.makedirs(out, exist_ok=True)
    subset.to_pickle(os.path.join(out, "gold.pkl"))

    # Reuse EDI_demo's synonyms and stopwords so scoring matches the full dataset.
    for name in ["synonyms.json", "stopwords.json"]:
        with open(os.path.join(COLUMBO, "EDI_demo", name)) as f:
            data = json.load(f)
        with open(os.path.join(out, name), "w") as f:
            json.dump(data, f, indent=2)

    # Keep the table list in this repo so the evaluation can be reproduced and cited.
    with open(os.path.join(HERE, f"{args.dataset}_tables.txt"), "w") as f:
        f.write("\n".join(tables) + "\n")

    labeled = subset["gt_label"].notna() & (subset["gt_label"] != "")
    print(f"{len(subset)} columns ({labeled.sum()} labeled) from {len(tables)} tables -> {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dataset", help="name of the folder to create under Columbo's clean_data/")
    parser.add_argument("--tables", type=int, help="pick this many random tables instead of the smoke-test tables")
    parser.add_argument("--seed", type=int, default=42)
    main(parser.parse_args())
