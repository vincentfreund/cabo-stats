"""Multiplayer Elo ratings based on final game placements.

Each game is broken into pairwise duels: for every pair of players, the one
with the better placement "beat" the other (a tie is a draw). Rating changes
from all duels in a game are computed against pre-game ratings, summed, and
scaled by 1/(n-1) so a game with more players doesn't swing ratings harder.
"""

from __future__ import annotations

from itertools import combinations

import pandas as pd

from .stats import game_results


def _expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))


def elo_history(df: pd.DataFrame, k: float = 32.0, start: float = 1500.0) -> pd.DataFrame:
    """Rating of every player after every game. Columns: game, game_order, player, elo."""
    games = game_results(df)
    ratings: dict[str, float] = {}
    rows = []

    for (order, game), g in games.groupby(["game_order", "game"], sort=True):
        players = list(g["player"])
        for p in players:
            ratings.setdefault(p, start)
        place = dict(zip(g["player"], g["place"]))
        delta = {p: 0.0 for p in players}
        n = len(players)

        for a, b in combinations(players, 2):
            ea = _expected(ratings[a], ratings[b])
            sa = 1.0 if place[a] < place[b] else 0.0 if place[a] > place[b] else 0.5
            delta[a] += k * (sa - ea)
            delta[b] += k * ((1 - sa) - (1 - ea))

        for p in players:
            ratings[p] += delta[p] / max(n - 1, 1)

        for p, r in ratings.items():
            rows.append({"game_order": order, "game": game, "player": p, "elo": round(r, 1)})

    return pd.DataFrame(rows)


def current_elo(df: pd.DataFrame, **kwargs) -> pd.Series:
    """Latest Elo rating per player, highest first."""
    hist = elo_history(df, **kwargs)
    last = hist[hist["game_order"] == hist["game_order"].max()]
    return last.set_index("player")["elo"].sort_values(ascending=False)
