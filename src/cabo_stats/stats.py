"""Descriptive statistics: leaderboards, records and head-to-head numbers.

In Cabo, LOWER is better – both for a single round and for the game total.
"""

from __future__ import annotations

import pandas as pd


def running_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Rows with a ``total`` column: each player's running total within a game (incl. resets)."""
    out = df.copy()
    if "total" not in out:
        out["total"] = out.groupby(["game", "player"])["score"].cumsum()
    return out


def _round_winners(df: pd.DataFrame) -> pd.DataFrame:
    """Rows of players who had the (shared) lowest score in their round."""
    low = df.groupby(["game", "round"])["score"].transform("min")
    return df[df["score"] == low]


def game_results(df: pd.DataFrame) -> pd.DataFrame:
    """One row per player per game with final total and placement (1 = winner)."""
    t = running_totals(df)
    last = t.sort_values("round").groupby(["game_order", "game", "player"], as_index=False).last()
    totals = last[["game_order", "game", "player", "total"]].rename(columns={"total": "final_total"})
    if "place" in df and df["place"].notna().all():
        place = df.groupby(["game", "player"])["place"].first()
        totals["place"] = [int(place[(g, p)]) for g, p in zip(totals["game"], totals["player"])]
    else:
        totals["place"] = totals.groupby("game")["final_total"].rank(method="min").astype(int)
    if "group" in df:
        grp = df.groupby("game")["group"].first()
        totals["group"] = totals["game"].map(grp)
    totals["won"] = totals["place"] == 1
    return totals.sort_values(["game_order", "place", "player"]).reset_index(drop=True)


def player_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Leaderboard with game- and round-level statistics per player."""
    games = game_results(df)
    winners = _round_winners(df)

    g = games.groupby("player").agg(
        games=("game", "nunique"),
        game_wins=("won", "sum"),
        avg_place=("place", "mean"),
        avg_final_total=("final_total", "mean"),
    )
    r = df.groupby("player").agg(
        rounds=("score", "size"),
        avg_round=("score", "mean"),
        median_round=("score", "median"),
        best_round=("score", "min"),
        worst_round=("score", "max"),
        zero_rounds=("score", lambda s: int((s == 0).sum())),
        cabo_calls=("called_cabo", "sum"),
        resets=("reset", "sum"),
    )
    rw = winners.groupby("player").size().rename("round_wins")

    # A Cabo call is "successful" if it was recorded as won, or – without a
    # cabo_result column – if the caller had the lowest score that round.
    calls = df[df["called_cabo"] == 1].copy()
    if not calls.empty and "cabo_result" in calls:
        succ = (calls["cabo_result"] == "won").groupby(calls["player"]).sum()
    elif not calls.empty:
        low = df.groupby(["game", "round"])["score"].min().rename("round_low")
        calls = calls.join(low, on=["game", "round"])
        succ = (calls["score"] == calls["round_low"]).groupby(calls["player"]).sum()
    else:
        succ = pd.Series(dtype=int)

    out = g.join(r).join(rw).fillna({"round_wins": 0})
    out["round_wins"] = out["round_wins"].astype(int)
    out["game_win_rate"] = out["game_wins"] / out["games"]
    out["round_win_rate"] = out["round_wins"] / out["rounds"]
    out["cabo_success"] = succ.reindex(out.index).fillna(0).astype(int)
    out["cabo_success_rate"] = (out["cabo_success"] / out["cabo_calls"]).where(
        out["cabo_calls"] > 0
    )

    cols = [
        "games", "game_wins", "game_win_rate", "avg_place", "avg_final_total",
        "rounds", "round_wins", "round_win_rate", "avg_round", "median_round",
        "best_round", "worst_round", "zero_rounds",
        "cabo_calls", "cabo_success", "cabo_success_rate", "resets",
    ]
    return out[cols].sort_values(["game_win_rate", "avg_round"], ascending=[False, True])


def _longest_streak(flags: list[bool]) -> int:
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def records(df: pd.DataFrame) -> pd.DataFrame:
    """A table of notable records: worst round, best game, streaks, comebacks."""
    rows = []
    games = game_results(df)
    totals = running_totals(df)

    worst = df.loc[df["score"].idxmax()]
    rows.append(("Highest single round", worst["player"], int(worst["score"]),
                 f"game {worst['game']}, round {worst['round']}"))

    best_game = games.loc[games["final_total"].idxmin()]
    rows.append(("Lowest game total", best_game["player"], int(best_game["final_total"]),
                 f"game {best_game['game']}"))

    worst_game = games.loc[games["final_total"].idxmax()]
    rows.append(("Highest game total", worst_game["player"], int(worst_game["final_total"]),
                 f"game {worst_game['game']}"))

    # Longest streak of round wins (across games, in chronological order).
    low = df.groupby(["game", "round"])["score"].transform("min")
    seq = df.assign(win=df["score"] == low).sort_values(["game_order", "round"])
    best_streak = max(
        ((p, _longest_streak(list(s["win"]))) for p, s in seq.groupby("player")),
        key=lambda x: x[1],
    )
    rows.append(("Longest round-win streak", best_streak[0], best_streak[1], "rounds in a row"))

    zeros = df[df["score"] == 0].groupby("player").size()
    if not zeros.empty:
        rows.append(("Most zero-point rounds", zeros.idxmax(), int(zeros.max()), "all games"))

    # Biggest comeback: the winner's largest deficit to the leader at any point.
    best_cb = None
    for game, t in totals.groupby("game"):
        winner_rows = games[(games["game"] == game) & games["won"]]
        lead = t.groupby("round")["total"].min()
        for w in winner_rows["player"]:
            mine = t[t["player"] == w].set_index("round")["total"]
            deficit = int((mine - lead.reindex(mine.index)).max())
            if best_cb is None or deficit > best_cb[1]:
                best_cb = (w, deficit, game)
    if best_cb and best_cb[1] > 0:
        rows.append(("Biggest comeback", best_cb[0], best_cb[1],
                     f"points behind the leader, still won game {best_cb[2]}"))

    resets = df[df["reset"] == 1].groupby("player").size()
    if not resets.empty:
        rows.append(("Most resets", resets.idxmax(), int(resets.max()), "all games"))

    longest = df.groupby("game")["round"].max()
    rows.append(("Longest game", "–", int(longest.max()), f"rounds (game {longest.idxmax()})"))

    return pd.DataFrame(rows, columns=["record", "player", "value", "context"])


def head_to_head(df: pd.DataFrame) -> pd.DataFrame:
    """Share of shared rounds in which the row player scored lower than the column player."""
    wide = df.pivot_table(index=["game", "round"], columns="player", values="score")
    players = list(wide.columns)
    mat = pd.DataFrame(index=players, columns=players, dtype=float)
    for a in players:
        for b in players:
            if a == b:
                continue
            both = wide[[a, b]].dropna()
            mat.loc[a, b] = (both[a] < both[b]).mean() if len(both) else float("nan")
    return mat


def chaos_rule_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Average points and round wins per chaos rule (rows without a rule are skipped)."""
    d = df[df["chaos_rule"].notna() & (df["chaos_rule"].astype(str).str.len() > 0)]
    if d.empty:
        return pd.DataFrame(columns=["rounds", "avg_points", "top_round_winner"])
    low = d.groupby(["game", "round"])["score"].transform("min")
    wins = d[d["score"] == low]
    out = d.groupby("chaos_rule").agg(
        rounds=("round", lambda s: d.loc[s.index, ["game", "round"]].drop_duplicates().shape[0]),
        avg_points=("score", "mean"),
    )
    top = wins.groupby(["chaos_rule", "player"]).size().reset_index(name="n")
    top = top.sort_values("n", ascending=False).drop_duplicates("chaos_rule").set_index("chaos_rule")
    out["top_round_winner"] = top["player"] + " (" + top["n"].astype(str) + ")"
    return out.sort_values("rounds", ascending=False)
