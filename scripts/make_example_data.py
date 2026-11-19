"""Generate a synthetic example dataset (data/example_rounds.csv).

The numbers are made up – they only exist so the repo works out of the box.
Replace them with your own games (see README → "Your own data").
"""

from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
players = {"Alice": 6.0, "Bob": 7.5, "Chris": 8.5}  # mean round score (lower = stronger)
rows = []
dates = pd.date_range("2026-09-05", periods=6, freq="7D")

for g, date in enumerate(dates, start=1):
    totals = dict.fromkeys(players, 0)
    rnd = 0
    while max(totals.values()) <= 100:
        rnd += 1
        caller = rng.choice(list(players))
        raw = {p: int(max(0, rng.normal(m, 5))) for p, m in players.items()}
        low = min(raw.values())
        scores = {}
        for p, s in raw.items():
            if p == caller:
                # Successful call → 0 points, failed call → +5 penalty.
                s = 0 if raw[p] == low else s + 5
            scores[p] = s
        for p, s in scores.items():
            totals[p] += s
            if totals[p] == 100:  # house rule: exactly 100 resets to 50
                s -= 50
                totals[p] = 50
            rows.append({"game": g, "date": date.date().isoformat(), "round": rnd,
                         "player": p, "score": s, "called_cabo": int(p == caller)})

out = Path(__file__).resolve().parents[1] / "data" / "example_rounds.csv"
out.parent.mkdir(exist_ok=True)
pd.DataFrame(rows).to_csv(out, index=False)
print(f"wrote {len(rows)} rows to {out}")
