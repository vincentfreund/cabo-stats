"""Loading and validating round-level Cabo data.

The canonical format is a *long* table with one row per player per round:

    game,date,round,player,score,called_cabo
    1,2026-10-03,1,Alice,4,0
    1,2026-10-03,1,Bob,0,1

Required: ``game``, ``round``, ``player``, ``score`` (points that round, lower is better).

Optional, used when present:

* ``date``, ``group``          – shown and filterable in the dashboard
* ``called_cabo``              – 1/yes if the player called Cabo that round
* ``cabo_result``              – won / tied / missed (otherwise derived from scores)
* ``total``                    – running total after the round, incl. resets
* ``reset``                    – 1/yes if a reset (e.g. exactly 50 → 25, 100 → 50) happened
* ``place``                    – final placement in the game (1 = winner)
* ``chaos_rule``               – name of a special rule active that round

Column names from the Cabo score-tracker site export are recognised
automatically (``game_no``, ``round_score``, ``total_after_round``,
``final_place`` …), as are a few common alternatives (``points``, ``punkte``,
``spiel`` …).

Resets: when ``total`` and ``reset`` are present, the round score of a reset
row is rebuilt as *points before the reset* (= 2 × total after the reset −
previous total), so a reset never looks like a −38 "round". Totals and final
placements are always taken from the file when available.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED = ["game", "round", "player", "score"]

ALIASES: dict[str, list[str]] = {
    "game": ["game_no", "game_nr", "game_id", "match", "spiel", "partie"],
    "round": ["round_no", "runde"],
    "player": ["name", "spieler"],
    "score": ["round_score", "points", "punkte", "pts"],
    "total": ["total_after_round", "running_total", "gesamt"],
    "place": ["final_place", "placement", "platz"],
    "called_cabo": ["cabo", "cabo_called"],
    "chaos_rule": ["chaos", "rule"],
}

TRUTHY = {"1", "yes", "y", "true", "ja", "x", "✓"}


class DataError(ValueError):
    """Raised when the input data does not follow the expected format."""


def load_rounds(path: str | Path) -> pd.DataFrame:
    """Read a CSV and return a validated DataFrame."""
    return validate_rounds(pd.read_csv(path))


def _flag(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.lower().isin(TRUTHY).astype(int)


def _apply_aliases(df: pd.DataFrame) -> pd.DataFrame:
    cols = set(df.columns)
    rename = {}
    for canon, alts in ALIASES.items():
        if canon in cols:
            continue
        for alt in alts:
            if alt in cols:
                rename[alt] = canon
                break
    return df.rename(columns=rename)


def validate_rounds(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise columns and types, rebuild reset rounds, sort, and return a copy."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = _apply_aliases(df)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DataError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Found: {', '.join(df.columns)}"
        )

    df["player"] = df["player"].astype(str).str.strip()
    df["round"] = pd.to_numeric(df["round"], errors="raise").astype(int)
    df["score"] = pd.to_numeric(df["score"], errors="raise").astype(int)
    df["called_cabo"] = _flag(df["called_cabo"]) if "called_cabo" in df else 0
    df["reset"] = _flag(df["reset"]) if "reset" in df else 0
    if "cabo_result" in df:
        df["cabo_result"] = df["cabo_result"].fillna("").astype(str).str.strip().str.lower()
    for col in ("date", "group", "chaos_rule"):
        if col not in df:
            df[col] = None

    dupes = df.duplicated(subset=["game", "round", "player"])
    if dupes.any():
        first = df[dupes].iloc[0]
        raise DataError(
            f"Duplicate entry: game {first['game']}, round {first['round']}, "
            f"player {first['player']}"
        )

    # Keep games in the order they first appear in the file.
    order = {g: i for i, g in enumerate(pd.unique(df["game"]))}
    df["game_order"] = df["game"].map(order)
    df = df.sort_values(["game_order", "round", "player"]).reset_index(drop=True)

    if "total" in df:
        df["total"] = pd.to_numeric(df["total"], errors="coerce")
        prev = df.groupby(["game", "player"])["total"].shift(1).fillna(0)
        rebuilt = (2 * df["total"] - prev).round()
        is_reset = (df["reset"] == 1) & df["total"].notna()
        df.loc[is_reset, "score"] = rebuilt[is_reset].astype(int)
        df["total"] = df["total"].fillna(df.groupby(["game", "player"])["score"].cumsum())
    else:
        df["total"] = df.groupby(["game", "player"])["score"].cumsum()
    df["total"] = df["total"].astype(int)

    if "place" in df:
        df["place"] = pd.to_numeric(df["place"], errors="coerce")
    return df
