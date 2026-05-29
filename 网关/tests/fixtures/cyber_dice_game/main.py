from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI
except ImportError:  # The tests exercise the game logic without starting ASGI.
    FastAPI = None


BANK_PATH = Path(__file__).with_name("players_bank.json")
LOG_PATH = Path(__file__).with_name("game_log.txt")


app = FastAPI(title="Cyber-Dice") if FastAPI else None


def load_bank() -> dict[str, int]:
    return json.loads(BANK_PATH.read_text(encoding="utf-8"))


def save_bank(bank: dict[str, int]) -> None:
    BANK_PATH.write_text(json.dumps(bank, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def roll_dice() -> int:
    return random.randint(1, 6)


def settle_round(player: str, player_roll: int, house_roll: int, stake: int = 10) -> dict[str, Any]:
    if player_roll < 1 or player_roll > 6 or house_roll < 1 or house_roll > 6:
        raise ValueError("dice roll must be between 1 and 6")
    if stake <= 0:
        raise ValueError("stake must be positive")

    bank = load_bank()
    current = int(bank.get(player, 0))
    if player_roll > house_roll:
        current += stake
        outcome = "win"
    elif player_roll < house_roll:
        current -= stake * 2
        outcome = "loss"
    else:
        outcome = "draw"
    bank[player] = current
    save_bank(bank)
    LOG_PATH.write_text(f"{player},{player_roll},{house_roll},{stake},{outcome}\n", encoding="utf-8")
    return {"player": player, "balance": current, "outcome": outcome}


if app is not None:

    @app.post("/round/{player}")
    def play_round(player: str, stake: int = 10) -> dict[str, Any]:
        return settle_round(player, roll_dice(), roll_dice(), stake)
