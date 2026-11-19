"""Command line interface.

    cabo-stats report data/example_rounds.csv
    cabo-stats odds data/example_rounds.csv --totals Alice=42 Bob=61 Chris=55
"""

from __future__ import annotations

import argparse

import pandas as pd

from .data import load_rounds
from .elo import current_elo
from .simulate import win_probability
from .stats import head_to_head, player_summary, records


def _fmt(df: pd.DataFrame) -> str:
    return df.round(2).to_markdown(floatfmt="g", missingval="–")


def cmd_report(args: argparse.Namespace) -> None:
    df = load_rounds(args.csv)
    n_games, n_rounds = df["game"].nunique(), df.groupby(["game", "round"]).ngroups
    print(f"# Cabo report\n\n{n_games} games, {n_rounds} rounds, "
          f"{df['player'].nunique()} players\n")
    print("## Leaderboard\n")
    s = player_summary(df)[["games", "game_wins", "game_win_rate", "round_wins",
                            "avg_round", "best_round", "worst_round", "cabo_calls"]]
    print(_fmt(s), "\n")
    print("## Elo\n")
    print(_fmt(current_elo(df).to_frame()), "\n")
    print("## Records\n")
    print(records(df).to_markdown(index=False), "\n")
    print("## Head-to-head (share of rounds row beat column)\n")
    print(_fmt(head_to_head(df)))


def cmd_odds(args: argparse.Namespace) -> None:
    df = load_rounds(args.csv)
    totals = {}
    for item in args.totals:
        name, _, value = item.partition("=")
        totals[name] = int(value)
    p = win_probability(totals, df, limit=args.limit, n_sims=args.sims)
    print(_fmt((p * 100).round(1).rename("win %").to_frame()))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="cabo-stats", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    rep = sub.add_parser("report", help="print a Markdown report")
    rep.add_argument("csv")
    rep.set_defaults(func=cmd_report)

    odds = sub.add_parser("odds", help="win probability for a game in progress")
    odds.add_argument("csv", help="historical rounds used for simulation")
    odds.add_argument("--totals", nargs="+", required=True, metavar="NAME=POINTS")
    odds.add_argument("--limit", type=int, default=100)
    odds.add_argument("--sims", type=int, default=10_000)
    odds.set_defaults(func=cmd_odds)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
