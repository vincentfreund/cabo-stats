"""Streamlit dashboard:  streamlit run app/dashboard.py"""

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from cabo_stats import (
    chaos_rule_stats, current_elo, elo_history, head_to_head, player_summary, records,
    running_totals, validate_rounds, win_probability,
)

EXAMPLE = Path(__file__).resolve().parents[1] / "data" / "example_rounds.csv"
DEFAULT = Path(os.environ.get("CABO_DATA", EXAMPLE))  # CABO_DATA=my.csv streamlit run …

st.set_page_config(page_title="Cabo Stats", page_icon="🃏", layout="wide")
st.title("Cabo Stats")

upload = st.sidebar.file_uploader("Upload your rounds CSV", type="csv")
raw = pd.read_csv(upload) if upload else pd.read_csv(DEFAULT)
if not upload and DEFAULT == EXAMPLE:
    st.sidebar.info("Showing the synthetic example data. Upload your own CSV to replace it.")

try:
    df = validate_rounds(raw)
except ValueError as e:
    st.error(f"Couldn't read this file: {e}")
    st.stop()

groups = [g for g in pd.unique(df["group"]) if pd.notna(g)]
if len(groups) > 1:
    chosen = st.sidebar.multiselect("Groups", groups, default=groups)
    df = df[df["group"].isin(chosen)]
    if df.empty:
        st.warning("Select at least one group.")
        st.stop()
summary = player_summary(df)

c1, c2, c3 = st.columns(3)
c1.metric("Games", df["game"].nunique())
c2.metric("Rounds", df.groupby(["game", "round"]).ngroups)
c3.metric("Players", df["player"].nunique())

tab_lb, tab_games, tab_elo, tab_h2h, tab_rec, tab_chaos, tab_odds = st.tabs(
    ["Leaderboard", "Games", "Elo", "Head-to-head", "Records", "Chaos rules", "Live odds"]
)

with tab_lb:
    st.dataframe(
        summary.style.format({
            "game_win_rate": "{:.0%}", "round_win_rate": "{:.0%}",
            "cabo_success_rate": "{:.0%}", "avg_place": "{:.2f}",
            "avg_final_total": "{:.1f}", "avg_round": "{:.2f}", "median_round": "{:.1f}",
            "cabo_calls": "{:.0f}", "cabo_success": "{:.0f}", "resets": "{:.0f}",
        }, na_rep="–"),
        width="stretch",
    )
    fig = px.box(df, x="player", y="score", points="all",
                 title="Round score distribution (lower is better)")
    st.plotly_chart(fig, width="stretch")

with tab_games:
    game = st.selectbox("Game", list(pd.unique(df["game"])))
    t = running_totals(df[df["game"] == game])
    fig = px.line(t, x="round", y="total", color="player", markers=True,
                  title=f"Running totals – game {game}")
    fig.add_hline(y=100, line_dash="dot", annotation_text="limit")
    st.plotly_chart(fig, width="stretch")

with tab_elo:
    hist = elo_history(df)
    fig = px.line(hist, x="game_order", y="elo", color="player", markers=True,
                  labels={"game_order": "game #"}, title="Elo after each game")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(current_elo(df).to_frame(), width="content")

with tab_h2h:
    st.caption("Share of rounds in which the ROW player scored lower than the COLUMN player.")
    st.dataframe(head_to_head(df).style.format("{:.0%}", na_rep="–"))

with tab_rec:
    st.dataframe(records(df), hide_index=True, width="stretch")

with tab_chaos:
    cr = chaos_rule_stats(df)
    if cr.empty:
        st.info("No chaos rules recorded in this data.")
    else:
        st.caption("Average points per player-round under each chaos rule (lower = friendlier rule).")
        st.dataframe(cr.style.format({"avg_points": "{:.1f}"}), width="stretch")

with tab_odds:
    st.write("Enter the current totals of a game in progress:")
    cols = st.columns(len(summary.index))
    totals = {p: cols[i].number_input(p, 0, 150, 0, key=f"t_{p}")
              for i, p in enumerate(summary.index)}
    limit = st.slider("Game ends when a total exceeds", 50, 150, 100)
    r100 = st.checkbox("Exactly 100 → back to 50", value=True)
    r50 = st.checkbox("Exactly 50 → back to 25", value=bool(df["reset"].any()))
    resets = {**({100: 50} if r100 else {}), **({50: 25} if r50 else {})}
    if st.button("Simulate 10,000 endings"):
        p = win_probability(totals, df, limit=limit, resets=resets)
        st.plotly_chart(px.bar(p.mul(100).round(1), labels={"value": "win %", "index": ""}),
                        width="stretch")
