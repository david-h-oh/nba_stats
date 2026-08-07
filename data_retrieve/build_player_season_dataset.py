"""Build leakage-safe player-season features and next-season targets from NBA game logs.

Each feature row uses only games from the named season.  Its matching label row
contains that same player's realized production in the following season.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import fmean, pstdev


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data"
OUTPUT = INPUT / "model"

COUNTING_STATS = ("FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "BLKA", "PF", "PTS")
RATE_STATS = ("MIN", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "REB", "AST", "TOV", "STL", "BLK", "PTS")


def number(value: str) -> float:
    return float(value) if value not in ("", None) else 0.0


def season_from_path(path: Path) -> int:
    return int(path.name.split("_")[1])


def summarize(player_id: str, player_name: str, season: int, games: list[dict[str, str]]) -> dict[str, float | int | str]:
    games = sorted(games, key=lambda game: game["GAME_DATE"])
    values = {stat: [number(game[stat]) for game in games] for stat in RATE_STATS}
    totals = {stat: sum(number(game[stat]) for game in games) for stat in COUNTING_STATS}
    game_count = len(games)
    minutes = values["MIN"]
    last_10 = games[-10:]
    first_10 = games[:10]
    first_date = datetime.fromisoformat(games[0]["GAME_DATE"]).date()
    last_date = datetime.fromisoformat(games[-1]["GAME_DATE"]).date()

    row: dict[str, float | int | str] = {
        "season_start": season,
        "next_season_start": season + 1,
        "PLAYER_ID": player_id,
        "PLAYER_NAME": player_name,
        "team_count": len({game["TEAM_ID"] for game in games}),
        "games": game_count,
        "active_days": (last_date - first_date).days + 1,
        "games_per_30_active_days": game_count / max(1, (last_date - first_date).days + 1) * 30,
        "min_mean": fmean(minutes),
        "min_std": pstdev(minutes) if game_count > 1 else 0.0,
        "min_last_10_mean": fmean([number(game["MIN"]) for game in last_10]),
        "min_trend_first10_to_last10": fmean([number(game["MIN"]) for game in last_10]) - fmean([number(game["MIN"]) for game in first_10]),
    }

    for stat in COUNTING_STATS:
        total = totals[stat]
        row[f"{stat.lower()}_total"] = total
        row[f"{stat.lower()}_per_game"] = total / game_count
        row[f"{stat.lower()}_per_36"] = total / max(sum(minutes), 1) * 36
        row[f"{stat.lower()}_last_10_per_game"] = sum(number(game[stat]) for game in last_10) / len(last_10)
        if stat in {"PTS", "REB", "AST", "STL", "BLK", "TOV"}:
            stat_values = [number(game[stat]) for game in games]
            row[f"{stat.lower()}_std"] = pstdev(stat_values) if game_count > 1 else 0.0

    row["fg_pct_weighted"] = totals["FGM"] / totals["FGA"] if totals["FGA"] else 0.0
    row["ft_pct_weighted"] = totals["FTM"] / totals["FTA"] if totals["FTA"] else 0.0
    row["fg3_pct_weighted"] = totals["FG3M"] / totals["FG3A"] if totals["FG3A"] else 0.0
    return row


def read_season(path: Path) -> list[dict[str, float | int | str]]:
    by_player: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as file:
        for game in csv.DictReader(file):
            # Null minutes are DNP records, not played games and should not
            # contribute to player production or availability features.
            if number(game["MIN"]) > 0:
                by_player[(game["PLAYER_ID"], game["PLAYER_NAME"])].append(game)
    season = season_from_path(path)
    return [summarize(player_id, player_name, season, games) for (player_id, player_name), games in by_player.items()]


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    paths = sorted(INPUT.glob("gamelogs_*_Reg.txt"), key=season_from_path)
    if not paths:
        raise FileNotFoundError(f"No regular-season logs found in {INPUT}")

    by_season = {season_from_path(path): read_season(path) for path in paths}
    feature_rows = [row for season in sorted(by_season) for row in by_season[season]]
    labels: list[dict[str, float | int | str]] = []

    for season, rows in by_season.items():
        next_season = by_season.get(season + 1, [])
        next_by_id = {str(row["PLAYER_ID"]): row for row in next_season}
        for row in rows:
            target = next_by_id.get(str(row["PLAYER_ID"]))
            if target is None:
                continue
            labels.append({
                "season_start": season,
                "PLAYER_ID": row["PLAYER_ID"],
                "PLAYER_NAME": row["PLAYER_NAME"],
                "target_games": target["games"],
                "target_min_per_game": target["min_mean"],
                "target_fg_pct_weighted": target["fg_pct_weighted"],
                "target_ft_pct_weighted": target["ft_pct_weighted"],
                **{f"target_{stat.lower()}_total": target[f"{stat.lower()}_total"] for stat in COUNTING_STATS},
                **{f"target_{stat.lower()}_per_game": target[f"{stat.lower()}_per_game"] for stat in ("FG3M", "PTS", "REB", "AST", "TOV", "STL", "BLK")},
            })

    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT / "player_season_features.csv", feature_rows)
    write_csv(OUTPUT / "next_season_labels.csv", labels)
    print(f"Wrote {len(feature_rows):,} feature rows and {len(labels):,} next-season label rows to {OUTPUT}")


if __name__ == "__main__":
    main()
