# 🃏 cabo-stats

Leaderboards, Elo ratings, records, head-to-head numbers and **live win probabilities** for the card game [Cabo](https://boardgamegeek.com/boardgame/232414/cabo). Record what happens at the table and get the full numbers: who is actually the best, whose Cabo calls are reckless, and how safe a 20-point lead really is.

```
$ cabo-stats odds data/example_rounds.csv --totals Alice=60 Bob=45 Chris=70
|       |   win % |
|:------|--------:|
| Bob   |    68.7 |
| Alice |    21.2 |
| Chris |    10.1 |
```

## Features

| | |
|---|---|
| **Leaderboard** | game wins, win rate, average placement, round wins, average/median/best/worst round, zero-point rounds |
| **Cabo calls** | how often each player calls Cabo and how often the call actually wins the round |
| **Elo ratings** | multiplayer Elo from final placements, tracked game by game |
| **Records** | highest round, best/worst game, longest round-win streak, biggest comeback, longest game |
| **Head-to-head** | share of rounds each player beat each other player |
| **Live odds** | Monte Carlo simulation of a game in progress, using each player's own score history |
| **Chaos rules** | average points and top round-winner under each chaos rule |
| **Groups** | filter the dashboard by playing group |
| **Dashboard** | Streamlit app with all of the above plus charts. Upload your CSV and go |

## Quick start

```bash
git clone https://github.com/vincentfreund/cabo-stats.git
cd cabo-stats
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[app,dev]"

cabo-stats report data/example_rounds.csv               # Markdown report in the terminal
streamlit run app/dashboard.py                          # interactive dashboard
pytest                                                  # run the tests
```

## Your own data

One row per player per round. Record the points a player **actually received** after your house rules (Cabo penalty, the exactly-100 → 50 reset, …). The engine doesn't need to know your rules.

```csv
game,date,round,player,score,called_cabo
1,2026-10-03,1,Vincent,4,0
1,2026-10-03,1,Nils,0,1
1,2026-10-03,1,Nelson,11,0
1,2026-10-03,2,Vincent,7,0
...
```

| column | required | meaning |
|---|---|---|
| `game` | ✔ | game id; games are ordered by first appearance in the file |
| `round` | ✔ | round number inside the game, starting at 1 |
| `player` | ✔ | player name |
| `score` | ✔ | points received in that round (lower is better) |
| `date` | | date of the game |
| `called_cabo` | | `1` / `yes` if this player called Cabo this round |
| `cabo_result` | | `won` / `tied` / `missed` |
| `total` | | running total after the round, incl. resets |
| `reset` | | `yes` if a reset happened |
| `place` | | final placement in the game |
| `group`, `chaos_rule` | | group filter and chaos-rule stats in the dashboard |

**Exports from the Cabo score-tracker site work as they are.** Columns like `game_no`, `round_score`, `total_after_round`, `cabo_result`, `reset`, `chaos_rule`, `group` and `final_place` are recognised automatically. Totals and placings are taken from the file. On reset rounds (exactly 50 → 25, exactly 100 → 50) the round score is rebuilt from the running totals, so a reset never shows up as a "−38 round".

Load your own file by default instead of uploading it every time:

```bash
CABO_DATA=path/to/cabo_rounds.csv streamlit run app/dashboard.py
```

Tip: keep the CSV in Google Sheets or Excel while you play, then export it. The bundled `data/example_rounds.csv` is **synthetic** (made by `scripts/make_example_data.py`).

## How the numbers work

**Round winner.** The lowest score in a round. Ties count as a win for everyone tied.

**Successful Cabo call.** The caller had the lowest score that round.

**Elo.** Every game is split into pairwise duels: whoever placed better beat the other. Rating changes are summed and divided by *(players − 1)*, so a 5-player game doesn't swing ratings harder than a 3-player one. K = 32, start = 1500.

**Win probability.** Starting from the current totals, the rest of the game is simulated 10,000 times. Each player's round scores are drawn from their own history (bootstrap). The game ends when someone passes the limit, and the lowest total wins. This assumes rounds are independent and form is constant: it's a simple model, but an honest one.

## Project structure

```
src/cabo_stats/
  data.py       load + validate the CSV
  stats.py      leaderboard, records, head-to-head
  elo.py        multiplayer Elo
  simulate.py   Monte Carlo win probability
  cli.py        `cabo-stats` command
app/dashboard.py   Streamlit app
tests/             pytest suite
```

## Ideas / roadmap

- [ ] "Expected points" per round, i.e. how good was the hand vs. the result
- [ ] Per-player Cabo call timing (early vs. late calls)
- [ ] Export a shareable season summary image
- [ ] Google Sheets live sync

## License

MIT
