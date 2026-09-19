import os

import pytest

import main


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "bets.db"
    monkeypatch.setattr(main, "DB_PATH", str(db_path))
    main.init_db()
    return db_path


def test_create_and_reveal_bet(isolated_db):
    client = main.app.test_client()

    response = client.post(
        "/bet/new",
        json={"player_id": "player-1", "amount": 5.5},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "bet_id" in payload
    assert "commit_hash" in payload

    bet_id = payload["bet_id"]
    reveal_response = client.post(
        "/bet/reveal",
        json={"bet_id": bet_id, "choice": "heads"},
    )

    assert reveal_response.status_code == 200
    reveal_payload = reveal_response.get_json()
    assert reveal_payload["result"] in {"heads", "tails"}
    assert "won" in reveal_payload
    assert "seed" in reveal_payload


def test_invalid_choice_is_rejected(isolated_db):
    client = main.app.test_client()

    new_bet = client.post(
        "/bet/new",
        json={"player_id": "player-2", "amount": 10},
    )
    bet_id = new_bet.get_json()["bet_id"]

    response = client.post(
        "/bet/reveal",
        json={"bet_id": bet_id, "choice": "sideways"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "choice must be 'heads' or 'tails'"


def test_amount_must_be_positive(isolated_db):
    client = main.app.test_client()

    response = client.post(
        "/bet/new",
        json={"player_id": "player-3", "amount": 0},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "amount must be a positive number"
