import pandas as pd
import pytest

from cabo_stats import (
    current_elo, game_results, head_to_head, player_summary, records,
    validate_rounds, win_probability,
)
from cabo_stats.data import DataError


@pytest.fixture
def tiny():
    # Game 1: A wins (5 vs 12), game 2: B wins (3 vs 20)
    rows = [
        (1, 1, "A", 0, 1), (1, 1, "B", 7, 0),
        (1, 2, "A", 5, 0), (1, 2, "B", 5, 0),
        (2, 1, "A", 10, 0), (2, 1, "B", 0, 1),
        (2, 2, "A", 10, 0), (2, 2, "B", 3, 0),
    ]
    return validate_rounds(pd.DataFrame(rows, columns=["game", "round", "player", "score", "called_cabo"]))


def test_missing_column_raises():
    with pytest.raises(DataError):
        validate_rounds(pd.DataFrame({"game": [1], "player": ["A"], "score": [1]}))


def test_duplicate_raises():
    df = pd.DataFrame({"game": [1, 1], "round": [1, 1], "player": ["A", "A"], "score": [1, 2]})
    with pytest.raises(DataError):
        validate_rounds(df)


def test_game_results(tiny):
    g = game_results(tiny)
    winners = g[g["won"]].set_index("game")["player"].to_dict()
    assert winners == {1: "A", 2: "B"}
    assert g.loc[(g.game == 1) & (g.player == "B"), "final_total"].item() == 12


def test_summary_counts(tiny):
    s = player_summary(tiny)
    assert s.loc["A", "games"] == 2
    assert s.loc["A", "game_wins"] == 1
    # Round 1.2 was a tie at 5 -> both get a round win
    assert s.loc["A", "round_wins"] == 2
    assert s.loc["B", "round_wins"] == 3
    assert s.loc["A", "cabo_success_rate"] == 1.0
    assert s.loc["B", "zero_rounds"] == 1


def test_head_to_head(tiny):
    h = head_to_head(tiny)
    assert h.loc["A", "B"] == pytest.approx(1 / 4)
    assert h.loc["B", "A"] == pytest.approx(2 / 4)


def test_records_has_rows(tiny):
    r = records(tiny)
    assert "Highest single round" in set(r["record"])


def test_elo_symmetric(tiny):
    e = current_elo(tiny)
    # One win each, two players: ratings stay centred on 1500
    assert e.sum() == pytest.approx(3000, abs=0.5)


def test_win_probability_sums_to_one(tiny):
    p = win_probability({"A": 10, "B": 90}, tiny, n_sims=2000)
    assert p.sum() == pytest.approx(1.0)
    assert p["A"] > p["B"]


def test_example_data_loads():
    from pathlib import Path
    from cabo_stats import load_rounds
    df = load_rounds(Path(__file__).resolve().parents[1] / "data" / "example_rounds.csv")
    assert df["game"].nunique() == 6
