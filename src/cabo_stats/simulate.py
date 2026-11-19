"""Monte Carlo win probability for a game in progress.

Given the current totals, we simulate the rest of the game many times. Each
simulated round draws every player's score from their own historical round
scores (bootstrap). The game ends once any total exceeds ``limit``; the lowest
total wins. Reset house rules are given as ``resets``, e.g. ``{100: 50}`` for
"landing exactly on 100 puts you back to 50", or ``{50: 25, 100: 50}``.

This is deliberately simple – rounds are treated as independent and players'
form doesn't change – but with real data it gives a surprisingly good feel for
"how safe is this lead?".
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def win_probability(
    current_totals: dict[str, int],
    history: pd.DataFrame,
    limit: int = 100,
    resets: dict[int, int] | None = None,
    n_sims: int = 10_000,
    max_rounds: int = 200,
    seed: int | None = 42,
) -> pd.Series:
    """Probability that each player wins from the given state.

    ``history`` is a validated rounds DataFrame used to sample round scores.
    Players with fewer than 5 recorded rounds borrow from everyone's pooled scores.
    """
    rng = np.random.default_rng(seed)
    resets = {100: 50} if resets is None else resets
    players = list(current_totals)
    pooled = history["score"].to_numpy()
    if pooled.size == 0:
        raise ValueError("history has no rounds to sample from")

    pools = {}
    for p in players:
        own = history.loc[history["player"] == p, "score"].to_numpy()
        pools[p] = own if own.size >= 5 else pooled

    start = np.array([current_totals[p] for p in players], dtype=float)
    wins = np.zeros(len(players))

    # Vectorised over simulations: totals has shape (n_sims, n_players).
    totals = np.tile(start, (n_sims, 1))
    active = np.ones(n_sims, dtype=bool)
    if (start > limit).any():
        active[:] = False

    for _ in range(max_rounds):
        if not active.any():
            break
        idx = np.flatnonzero(active)
        draws = np.column_stack([rng.choice(pools[p], size=idx.size) for p in players])
        new = totals[idx] + draws
        reset_new = new.copy()
        for hit, back in resets.items():
            reset_new = np.where(new == hit, back, reset_new)
        new = reset_new
        totals[idx] = new
        finished = (new > limit).any(axis=1)
        active[idx[finished]] = False

    # Lowest total wins; ties split the win.
    best = totals.min(axis=1, keepdims=True)
    is_best = totals == best
    wins = (is_best / is_best.sum(axis=1, keepdims=True)).sum(axis=0)
    return pd.Series(wins / n_sims, index=players, name="win_probability").sort_values(
        ascending=False
    )
