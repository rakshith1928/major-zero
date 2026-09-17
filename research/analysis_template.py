"""T13 analysis template (converts to analysis.ipynb for the paper).

Input: research/results/study_rows.csv with columns:
  participant, system (zerobus/redbus), task, booking_seconds, manual_fields,
  success (0/1), warnings_accepted, familiarity (1-5)
Output: paired Wilcoxon tests + summary tables -> research/results/study_stats.json
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    import pandas as pd
    from scipy.stats import wilcoxon

    rows = pd.read_csv(HERE / "results" / "study_rows.csv")
    stats = {}
    for metric in ("booking_seconds", "manual_fields"):
        a = rows[rows.system == "zerobus"].groupby("participant")[metric].mean()
        b = rows[rows.system == "redbus"].groupby("participant")[metric].mean()
        common = a.index.intersection(b.index)
        w = wilcoxon(a.loc[common], b.loc[common])
        stats[metric] = {
            "zerobus_mean": round(float(a.mean()), 2),
            "redbus_mean": round(float(b.mean()), 2),
            "wilcoxon_p": round(float(w.pvalue), 4),
        }
    succ = rows.groupby("system")["success"].mean().to_dict()
    stats["success_rate"] = {k: round(float(v), 3) for k, v in succ.items()}
    (HERE / "results" / "study_stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
