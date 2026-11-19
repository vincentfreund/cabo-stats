"""The Cabo score-tracker site export format (synthetic sample, same columns)."""

import io

import pandas as pd
import pytest

from cabo_stats import chaos_rule_stats, game_results, player_summary, validate_rounds, win_probability

CSV = """game_no,game_id,group,date,source,players_in_game,round,player,hand_entered,hand_counted,round_score,total_after_round,called_cabo,cabo_result,reset,chaos_rule,final_total,final_place,game_winner
1,g1,Crew,,imported,2,1,Ann,,,40,40,,,,,25,1,Ann
1,g1,Crew,,imported,2,1,Ben,,,30,30,,,,,57,2,Ann
1,g1,Crew,,imported,2,2,Ann,,,-15,25,,,yes,,25,1,Ann
1,g1,Crew,,imported,2,2,Ben,,,27,57,,,,,57,2,Ann
2,g2,Crew,2026-11-03,site,2,1,Ann,0,,-3,-3,yes,won,,Bounty,-3,1,Ann
2,g2,Crew,2026-11-03,site,2,1,Ben,8,,8,48,,,,Bounty,48,2,Ann
"""


@pytest.fixture
def df():
    return validate_rounds(pd.read_csv(io.StringIO(CSV)))


def test_columns_recognised(df):
    assert {"game", "score", "total", "place", "chaos_rule"} <= set(df.columns)
    assert df["called_cabo"].sum() == 1


def test_reset_round_rebuilt(df):
    # Ann: 40 + 10 = 50 → reset to 25; the file stores -15, the real round score is 10
    row = df[(df.game == 1) & (df["round"] == 2) & (df.player == "Ann")].iloc[0]
    assert row["score"] == 10
    assert row["total"] == 25


def test_totals_and_places_from_file(df):
    g = game_results(df).set_index(["game", "player"])
    assert g.loc[(1, "Ann"), "final_total"] == 25
    assert g.loc[(1, "Ann"), "place"] == 1


def test_cabo_result_used(df):
    s = player_summary(df)
    assert s.loc["Ann", "cabo_success"] == 1
    assert s.loc["Ann", "resets"] == 1


def test_chaos_rules(df):
    c = chaos_rule_stats(df)
    assert "Bounty" in c.index


def test_simulation_with_resets(df):
    p = win_probability({"Ann": 40, "Ben": 45}, df, resets={50: 25, 100: 50}, n_sims=500)
    assert p.sum() == pytest.approx(1)
