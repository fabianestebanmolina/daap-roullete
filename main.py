import hashlib
import secrets
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "bets.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            bet_id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            amount REAL NOT NULL,
            seed TEXT NOT NULL,
            commit_hash TEXT NOT NULL,
            revealed INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def generate_seed():
    return secrets.token_hex(16)  # 128 bits of randomness

def hash_seed(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()

@app.route("/bet/new", methods=["POST"])
def new_bet():
    data = request.get_json(silent=True) or {}
    player_id = data.get("player_id")
    amount = data.get("amount")

    if not player_id:
        return jsonify({"error": "player_id is required"}), 400

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a positive number"}), 400

    if amount <= 0:
        return jsonify({"error": "amount must be a positive number"}), 400

    seed = generate_seed()
    commit_hash = hash_seed(seed)
    bet_id = secrets.token_hex(8)

    conn = get_db()
    conn.execute(
        "INSERT INTO bets (bet_id, player_id, amount, seed, commit_hash, revealed) VALUES (?, ?, ?, ?, ?, 0)",
        (bet_id, player_id, amount, seed, commit_hash),
    )
    conn.commit()
    conn.close()

    # This is the only thing the player sees before betting: the hash, never the seed.
    return jsonify({"bet_id": bet_id, "commit_hash": commit_hash})

@app.route("/bet/reveal", methods=["POST"])
def reveal_bet():
    data = request.get_json(silent=True) or {}
    bet_id = data.get("bet_id")
    player_choice = data.get("choice")  # "heads" or "tails"

    if player_choice not in {"heads", "tails"}:
        return jsonify({"error": "choice must be 'heads' or 'tails'"}), 400

    conn = get_db()
    bet = conn.execute("SELECT * FROM bets WHERE bet_id = ?", (bet_id,)).fetchone()

    if not bet:
        conn.close()
        return jsonify({"error": "bet_id not found"}), 404
    if bet["revealed"]:
        conn.close()
        return jsonify({"error": "this bet has already been revealed"}), 400

    seed = bet["seed"]
    # Deterministic result from the seed: even = heads, odd = tails
    result = "heads" if int(seed, 16) % 2 == 0 else "tails"
    won = result == player_choice

    conn.execute("UPDATE bets SET revealed = 1 WHERE bet_id = ?", (bet_id,))
    conn.commit()
    conn.close()

    return jsonify({
        "seed": seed,                     # the player can verify the hash with this
        "original_commit_hash": bet["commit_hash"],
        "result": result,
        "won": won,
    })

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)