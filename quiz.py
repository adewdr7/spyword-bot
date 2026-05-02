from firebase_admin import firestore
from datetime import datetime, timezone
import random

def get_db():
    return firestore.client()

# alias untuk dipakai di bot.py
db = None  # tidak dipakai langsung

COST_SUBMIT = 22
COST_SHOW   = 10
COST_CLUE   = 6
REWARD_BASE = 22  # total reward pool per soal (dibagi per huruf)

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def mask_answer(answer: str, revealed: list[int]) -> str:
    """Tampilkan huruf yang sudah ditebak, sisanya _ (spasi tetap spasi)"""
    result = []
    for i, ch in enumerate(answer):
        if ch == " ":
            result.append(" ")
        elif i in revealed:
            result.append(ch)
        else:
            result.append("_")
    return " ".join(result) if " " not in answer else "".join(result)

def reward_per_letter(answer: str) -> int:
    """Hitung reward per huruf (bulatkan, tanpa desimal)"""
    letters = [c for c in answer if c != " "]
    if not letters:
        return 0
    return round(REWARD_BASE / len(letters))

def build_display(soal: dict) -> str:
    """Format tampilan soal lengkap"""
    q        = soal.get("question", "")
    answer   = soal.get("answer", "")
    revealed = soal.get("revealed", [])
    submitter= soal.get("submitter", "Anonim")
    lines = [
        f"**from:** {submitter}",
        f"**Q:** {q}",
        f"**A:** `{mask_answer(answer, revealed)}`",
    ]
    return "\n".join(lines)

# ─────────────────────────────────────────
#  FIRESTORE HELPERS
# ─────────────────────────────────────────
def get_active_soal(guild_id: str) -> tuple[str | None, dict | None]:
    """Ambil soal aktif untuk server ini. Returns (doc_id, data)"""
    docs = (
        get_db().collection("quiz_soal")
        .where("guild_id", "==", guild_id)
        .where("status", "==", "active")
        .limit(1)
        .stream()
    )
    for doc in docs:
        return doc.id, doc.to_dict()
    return None, None

def get_pool_soal(guild_id: str) -> list[tuple[str, dict]]:
    """Ambil semua soal pending untuk server ini."""
    docs = (
        get_db().collection("quiz_soal")
        .where("guild_id", "==", guild_id)
        .where("status", "==", "pending")
        .stream()
    )
    return [(d.id, d.to_dict()) for d in docs]

def activate_next_soal(guild_id: str) -> tuple[str | None, dict | None]:
    """Aktifkan soal berikutnya dari pool. Returns (doc_id, data)"""
    pool = get_pool_soal(guild_id)
    if not pool:
        return None, None
    doc_id, data = random.choice(pool)
    get_db().collection("quiz_soal").document(doc_id).update({"status": "active"})
    data["status"] = "active"
    return doc_id, data

def submit_soal(guild_id: str, question: str, answer: str,
                max_show: int, submitter_name: str, submitter_id: str) -> str:
    """Simpan soal baru ke Firestore. Returns doc_id."""
    # Tentukan status: active kalau belum ada soal aktif
    active_id, _ = get_active_soal(guild_id)
    status = "pending" if active_id else "active"

    data = {
        "guild_id":    guild_id,
        "question":    question,
        "answer":      answer,
        "max_show":    max_show,
        "revealed":    [],
        "submitter":   submitter_name,
        "submitter_id": submitter_id,
        "status":      status,
        "solvers":     {},   # {user_id: [indices_solved]}
        "createdAt":   datetime.now(timezone.utc),
    }
    ref = db.collection("quiz_soal").add(data)
    return ref[1].id

def reveal_random_letter(doc_id: str, soal: dict, count: int = 1) -> dict:
    """Reveal `count` huruf acak yang belum terlihat. Returns updated soal."""
    answer   = soal.get("answer", "")
    revealed = list(soal.get("revealed", []))
    hidden   = [i for i, c in enumerate(answer) if c != " " and i not in revealed]
    to_show  = random.sample(hidden, min(count, len(hidden)))
    revealed.extend(to_show)
    get_db().collection("quiz_soal").document(doc_id).update({"revealed": revealed})
    soal["revealed"] = revealed
    return soal

def try_fill(doc_id: str, soal: dict, position: int, letter: str,
             user_id: str, user_name: str) -> dict:
    """
    Coba isi posisi `position` (1-based) dengan `letter`.
    Returns dict berisi:
      correct    : bool
      already    : bool  (sudah pernah ditebak orang lain)
      reward     : int   (koin yang didapat, 0 kalau salah/sudah)
      completed  : bool  (semua huruf terbuka)
      new_balance: int   (saldo baru, diisi oleh caller)
    """
    answer   = soal.get("answer", "")
    revealed = list(soal.get("revealed", []))
    solvers  = dict(soal.get("solvers", {}))

    idx = position - 1  # convert ke 0-based
    if idx < 0 or idx >= len(answer):
        return {"correct": False, "already": False, "reward": 0,
                "completed": False, "new_balance": 0, "out_of_range": True}

    actual = answer[idx]

    # Sudah terbuka?
    if idx in revealed:
        return {"correct": False, "already": True, "reward": 0,
                "completed": False, "new_balance": 0, "out_of_range": False}

    if letter.upper() != actual.upper():
        return {"correct": False, "already": False, "reward": 0,
                "completed": False, "new_balance": 0, "out_of_range": False}

    # Benar!
    revealed.append(idx)
    reward = reward_per_letter(answer)

    # Catat solver
    if user_id not in solvers:
        solvers[user_id] = {"name": user_name, "indices": [], "earned": 0}
    solvers[user_id]["indices"].append(idx)
    solvers[user_id]["earned"] = solvers[user_id].get("earned", 0) + reward

    # Cek completed
    hidden_left = [i for i, c in enumerate(answer) if c != " " and i not in revealed]
    completed = len(hidden_left) == 0

    update_data = {
        "revealed": revealed,
        "solvers":  solvers,
    }
    if completed:
        update_data["status"] = "done"

    get_db().collection("quiz_soal").document(doc_id).update(update_data)
    soal["revealed"] = revealed
    soal["solvers"]  = solvers
    if completed:
        soal["status"] = "done"

    return {
        "correct":     True,
        "already":     False,
        "reward":      reward,
        "completed":   completed,
        "new_balance": 0,  # diisi oleh caller setelah add_coins
        "out_of_range": False,
    }
