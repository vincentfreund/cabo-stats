"""cabo-stats: statistics, ratings and win probabilities for the card game Cabo."""

from .data import load_rounds, validate_rounds
from .stats import (
    player_summary,
    game_results,
    records,
    head_to_head,
    running_totals,
    chaos_rule_stats,
)
from .elo import elo_history, current_elo
from .simulate import win_probability

__all__ = [
    "load_rounds",
    "validate_rounds",
    "player_summary",
    "game_results",
    "records",
    "head_to_head",
    "running_totals",
    "chaos_rule_stats",
    "elo_history",
    "current_elo",
    "win_probability",
]

__version__ = "0.1.0"
