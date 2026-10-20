# Columbo comparison

Compares mini-catalog's expansion prompt with [Columbo](https://github.com/anhaidgroup/columbo) on subsets of Columbo's `EDI_demo` benchmark. Results are summarized in the [main README](../../README.md#evaluation-against-columbo).

| File | What it does | Python environment |
|---|---|---|
| `make_subset.py` | Builds `EDI_mini` (3 fixed tables) or `EDI_main` (random tables) under Columbo's `clean_data/` | Columbo |
| `run_mine.py` | Runs mini-catalog's prompt on a dataset and saves `results/<dataset>_mine_<time>.csv` | mini-catalog |
| `score.py` | Scores prediction files with Columbo's evaluator, on all and on abbreviated columns | Columbo |
| `compare.py` | Lists abbreviated columns where two prediction files differ in correctness | Columbo |
| `EDI_main_tables.txt` | The 20 tables in `EDI_main` (seed 42) | |
| `results/` | All predictions, including Columbo's (`*_columbo_*.csv`, copied from its `pred_df.pkl`) | |

## Reproduce

Clone Columbo next to this repo (`~/github/columbo`) and install its requirements in its own virtual environment. Then:

```bash
# Columbo's environment
python experiments/columbo_eval/make_subset.py EDI_main --tables 20 --seed 42

# Columbo's environment, from ~/github/columbo/columbo
python main.py --dataset EDI_main --table table_name --column column_name --gt_label gt_label --api_key "$OPENAI_API_KEY"

# mini-catalog's environment
python experiments/columbo_eval/run_mine.py EDI_main

# Columbo's environment
python experiments/columbo_eval/score.py EDI_main experiments/columbo_eval/results/EDI_main_*.csv
python experiments/columbo_eval/compare.py EDI_main experiments/columbo_eval/results/A.csv experiments/columbo_eval/results/B.csv
```
