from firebase_admin import firestore
from datetime import datetime, timezone

def get_db():
    return firestore.client()

CLAIM_MIN = 66
CLAIM_MAX = 110
CLAIM_COOLDOWN_HOURS = 24

def get_user_coins(user_id: str) -> dict:
    ref = get_db().collection("users").document(user_id).get()
    if ref.exists:
        return ref.to_dict()
    return {"coins": 0, "lastClaim": None}

def set_user_coins(user_id: str, coins: int):
    get_db().collection("users").document(user_id).set(
        {"coins": coins}, merge=True
    )

def add_coins(user_id: str, amount: int) -> int:
    data = get_user_coins(user_id)
    new_balance = data.get("coins", 0) + amount
    get_db().collection("users").document(user_id).set(
        {"coins": new_balance}, merge=True
    )
    return new_balance

def deduct_coins(user_id: str, amount: int) -> tuple[bool, int]:
    """Returns (success, new_balance)"""
    data = get_user_coins(user_id)
    current = data.get("coins", 0)
    if current < amount:
        return False, current
    new_balance = current - amount
    get_db().collection("users").document(user_id).set(
        {"coins": new_balance}, merge=True
    )
    return True, new_balance

def can_claim(user_id: str) -> tuple[bool, int]:
    """Returns (can_claim, seconds_remaining)"""
    data = get_user_coins(user_id)
    last_claim = data.get("lastClaim")
    if not last_claim:
        return True, 0
    now = datetime.now(timezone.utc)
    if hasattr(last_claim, "tzinfo") and last_claim.tzinfo is None:
        last_claim = last_claim.replace(tzinfo=timezone.utc)
    diff = (now - last_claim).total_seconds()
    cooldown = CLAIM_COOLDOWN_HOURS * 3600
    if diff >= cooldown:
        return True, 0
    return False, int(cooldown - diff)

def do_claim(user_id: str) -> tuple[bool, int, int]:
    """Returns (success, coins_gained, new_balance)"""
    import random
    claimable, _ = can_claim(user_id)
    if not claimable:
        return False, 0, get_user_coins(user_id).get("coins", 0)
    gained = random.randint(CLAIM_MIN, CLAIM_MAX)
    data = get_user_coins(user_id)
    current = data.get("coins", 0)
    new_balance = current + gained
    get_db().collection("users").document(user_id).set({
        "coins": new_balance,
        "lastClaim": datetime.now(timezone.utc)
    }, merge=True)
    return True, gained, new_balance

def format_seconds(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h} jam {m} menit"
    elif m > 0:
        return f"{m} menit {s} detik"
    return f"{s} detik"
