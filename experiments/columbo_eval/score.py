"""Score predictions with Columbo's own evaluator, so every system is measured the same way.

Run with Columbo's .venv:
    python experiments/columbo_eval/score.py DATASET PREDICTIONS [PREDICTIONS ...]

DATASET is a folder under Columbo's clean_data/ (e.g. EDI_main).
PREDICTIONS is a CSV from run_mine.py, or a pred_df.pkl saved by Columbo.

Each file is scored twice: on all labeled columns, and on abbreviated columns only
(where the column name and the gold label differ after lowercasing and dropping
non-alphanumerics, e.g. "DO_Percent_Sat" vs. "dissolved oxygen percent saturation").
"""
import contextlib
import io
import json
import os
import re
import sys
import warnings

import pandas as pd

COLUMBO_CODE = os.path.expanduser("~/github/columbo/columbo")
DATASETS = os.path.expanduser("~/github/columbo/clean_data")

sys.path.insert(0, COLUMBO_CODE)
from evaluate_with_synonyms import evaluate_w_synonyms  # noqa: E402

# Columbo's evaluator triggers pandas copy warnings that do not affect the scores.
# (pandas 3 removed this warning class, so look it up instead of assuming it exists.)
copy_warning = getattr(pd.errors, "SettingWithCopyWarning", None)
if copy_warning:
    warnings.filterwarnings("ignore", category=copy_warning)


def load_predictions(path):
    if path.endswith(".pkl"):
        return pd.read_pickle(path)
    # keep_default_na=False keeps names like "NA" as text; empty predictions stay "".
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def is_abbreviated(column_name, gt_label):
    normalize = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    return normalize(column_name) != normalize(gt_label)


def columbo_scores(predictions, gold, synonyms, stopwords):
    """Run Columbo's evaluator and return (exact match, F1) from what it prints."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        evaluate_w_synonyms(predictions, gold, synonyms, stopwords,
                            "table_name", "column_name", "gt_label", "PREDICTION")
    scores = [float(x) for x in re.findall(r"is: ([0-9.]+)", printed.getvalue())]
    return scores[0], scores[1]


def main(dataset, paths):
    folder = os.path.join(DATASETS, dataset)
    gold = pd.read_pickle(os.path.join(folder, "gold.pkl"))
    with open(os.path.join(folder, "synonyms.json")) as f:
        synonyms = json.load(f)
    with open(os.path.join(folder, "stopwords.json")) as f:
        stopwords = json.load(f)

    labeled = gold[gold["gt_label"].notna() & (gold["gt_label"] != "")]
    abbreviated = labeled[labeled.apply(lambda r: is_abbreviated(r["column_name"], r["gt_label"]), axis=1)]
    # flush before Columbo's evaluator forks workers, or each worker re-prints the buffer
    print(f"{dataset}: {len(labeled)} labeled columns, {len(abbreviated)} abbreviated\n", flush=True)

    rows = []
    for path in paths:
        predictions = load_predictions(path)
        empty = int((predictions["PREDICTION"].fillna("") == "").sum())
        em, f1 = columbo_scores(predictions, labeled, synonyms, stopwords)
        abbr_em, abbr_f1 = columbo_scores(predictions, abbreviated, synonyms, stopwords)
        rows.append({"file": os.path.basename(os.path.dirname(path)) + "/" + os.path.basename(path)
                     if path.endswith(".pkl") else os.path.basename(path),
                     "EM": em, "F1": f1, "abbr EM": abbr_em, "abbr F1": abbr_f1, "empty": empty})

    print(pd.DataFrame(rows).to_string(index=False, float_format="%.3f"))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
