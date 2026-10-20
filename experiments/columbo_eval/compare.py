"""List abbreviated columns where two prediction files disagree on correctness.

Run with Columbo's .venv:
    python experiments/columbo_eval/compare.py DATASET A.csv B.csv

A column counts as correct when Columbo's exact-match score (with synonyms and
stopwords) is 1, the same rule score.py uses.
"""
import json
import os
import sys
import warnings

import pandas as pd

from score import DATASETS, is_abbreviated, load_predictions

sys.path.insert(0, os.path.expanduser("~/github/columbo/columbo"))
from evaluate_with_synonyms import generate_synonym_sentences_dp, refine_LLM_expansion  # noqa: E402
from src.metric import BNGMetrics  # noqa: E402

warnings.filterwarnings("ignore")


def synonym_table(synonyms):
    """Make synonyms symmetric, the same way evaluate_w_synonyms does."""
    table = {}
    for key, value in synonyms.items():
        if isinstance(value, str):
            table[key.lower()] = {value.lower()}
            table[value.lower()] = {key.lower()}
        else:
            table[key.lower()] = {v.lower() for v in value}
            for v in value:
                table[v.lower()] = {key.lower()} | {x.lower() for x in value if x != v}
    return {k: list(v) for k, v in table.items()}


def main(dataset, path_a, path_b):
    folder = os.path.join(DATASETS, dataset)
    gold = pd.read_pickle(os.path.join(folder, "gold.pkl"))
    with open(os.path.join(folder, "synonyms.json")) as f:
        synonyms = synonym_table(json.load(f))
    with open(os.path.join(folder, "stopwords.json")) as f:
        stopwords = json.load(f)
    metric = BNGMetrics(["squad"], device="cpu")

    def exact_match(prediction, gold_label):
        if not prediction:
            return 0
        references = generate_synonym_sentences_dp(gold_label.lower(), synonyms, stopwords)
        predictions = [refine_LLM_expansion(stopwords, prediction)] * len(references)
        scores = metric.compute_scores(predictions=predictions, references=references, level="individual")
        return max(scores["individual_squad-em"])

    keys = ["table_name", "column_name"]
    rows = gold[gold["gt_label"].notna() & (gold["gt_label"] != "")][keys + ["gt_label"]]
    rows = rows[rows.apply(lambda r: is_abbreviated(r["column_name"], r["gt_label"]), axis=1)]
    for label, path in [("A", path_a), ("B", path_b)]:
        predictions = load_predictions(path).rename(columns={"PREDICTION": label})
        rows = rows.merge(predictions[keys + [label]], on=keys, how="left")
        rows[label] = rows[label].fillna("")
        rows[label + "_ok"] = [exact_match(p, g) for p, g in zip(rows[label], rows["gt_label"])]

    print(f"A = {os.path.basename(path_a)}\nB = {os.path.basename(path_b)}\n")
    shown = ["column_name", "gt_label", "A", "B"]
    groups = [
        ("A right, B wrong", (rows["A_ok"] == 1) & (rows["B_ok"] == 0)),
        ("B right, A wrong", (rows["A_ok"] == 0) & (rows["B_ok"] == 1)),
        ("both wrong", (rows["A_ok"] == 0) & (rows["B_ok"] == 0)),
    ]
    for title, mask in groups:
        print(f"{title} ({mask.sum()} of {len(rows)} abbreviated columns)")
        if mask.any():
            print(rows[mask][shown].to_string(index=False))
        print()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
