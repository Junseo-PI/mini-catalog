"""Run mini-catalog's enrichment prompt on a Columbo dataset and save the predictions as CSV.

Run with mini-catalog's .venv:
    python experiments/columbo_eval/run_mine.py EDI_main

Then score the CSV with Columbo's .venv (see score.py).
"""
import os
import sys
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "catalog"))

DATASETS = os.path.expanduser("~/github/columbo/clean_data")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# The CSV that score.py reads: one row per column, an empty PREDICTION counts as wrong.
PRED_COLUMNS = ["table_name", "column_name", "PREDICTION"]


def save_predictions(rows, name="mine"):
    """Save a list of {table_name, column_name, PREDICTION} dicts and return the file path."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"{name}_{datetime.now():%m%d_%H%M%S}.csv")
    pd.DataFrame(rows, columns=PRED_COLUMNS).to_csv(path, index=False)
    print(f"Saved {len(rows)} predictions to {path}")
    return path


def main(dataset):
    from enrich import check_result, enrich_table

    load_dotenv()
    client = OpenAI()
    gold = pd.read_pickle(os.path.join(DATASETS, dataset, "gold.pkl"))
    rows = []

    for table_name, table in gold.groupby("table_name", sort=False):
        column_names = table["column_name"].tolist()
        profile = {
            "table_name": table_name,
            "n_rows": None,
            "n_cols": len(column_names),
            "columns": [{"name": name} for name in column_names],
        }
        predictions = {name: "" for name in column_names}
        try:
            result = enrich_table(client, profile)
            if check_result(profile, result):
                predictions = {
                    column["name"]: column.get("expanded", "")
                    for column in result["columns"]
                }
            else:
                print(f"Failed {table_name}: result does not match the profile")
        except Exception as e:
            print(f"Failed {table_name}: {e}")

        rows.extend(
            {"table_name": table_name, "column_name": name,
             "PREDICTION": predictions[name]}
            for name in column_names
        )

    save_predictions(rows, name=f"{dataset}_mine")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "EDI_mini")
