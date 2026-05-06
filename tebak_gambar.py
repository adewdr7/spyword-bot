"""
tebak_gambar.py
===============
Modul Tebak Gambar untuk bot Discord.
Di-import di bot.py seperti quiz.py.

Koleksi Firestore yang digunakan:
  - tebak_gambar      : pool soal (draft/pending/approved/rejected/active/done)
  - tg_state          : state soal aktif per guild
  - tg_members        : user yang sudah !tgjoin per guild
  - discord_verify    : kode verifikasi sementara (TTL ditangani manual)
  - users             : field tambahan discordId, discordName, isVerified,
                        tgSubmitToday, tgSubmitDate, role (viewer/admin)

Command yang didaftarkan di bot.py:
  !v        — generate kode verifikasi 32 karakter (DM saja)
  !tg       — tampilkan soal tebak gambar aktif
  !jg       — jawab soal tebak gambar
  !tgjoin   — bergabung ke sesi tebak gambar server ini
"""

from firebase_admin import firestore
from datetime import datetime, timezone, timedelta
import random
import string

# ─────────────────────────────────────────────────────────────────
#  KONSTANTA
# ─────────────────────────────────────────────────────────────────
REWARD_MIN       = 30
REWARD_MAX       = 90
VERIFY_TTL_HOURS = 24          # kode verifikasi kedaluwarsa setelah 24 jam
VERIFY_CODE_LEN  = 32

# ─────────────────────────────────────────────────────────────────
#  HELPER DB
# ─────────────────────────────────────────────────────────────────
def get_db():
    return firestore.client()


# ─────────────────────────────────────────────────────────────────
#  VERIFIKASI DISCORD
# ─────────────────────────────────────────────────────────────────
def generate_verify_code(discord_id: str, discord_name: str) -> str:
    """
    Buat kode verifikasi 32 karakter (huruf kecil + besar + angka + simbol)
    dan simpan ke Firestore koleksi discord_verify.
    Jika sudah ada kode aktif untuk discord_id ini, timpa dengan yang baru.
    Returns kode yang dibuat.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    code = "".join(random.choices(alphabet, k=VERIFY_CODE_LEN))

    get_db().collection("discord_verify").document(discord_id).set({
        "discord_id"  : discord_id,
        "discord_name": discord_name,
        "code"        : code,
        "createdAt"   : datetime.now(timezone.utc),
        "used"        : False,
    })
    return code


def validate_verify_code(code: str) -> dict | None:
    """
    Cari kode verifikasi di Firestore.
    Returns dokumen data jika valid & belum kedaluwarsa, None jika tidak.
    """
    docs = (
        get_db().collection("discord_verify")
        .where("code", "==", code)
        .where("used", "==", False)
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict()
        created = data.get("createdAt")
        if created:
            # Normalisasi timezone
            if hasattr(created, "tzinfo") and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            if age_hours > VERIFY_TTL_HOURS:
                return None   # kedaluwarsa
        # Tandai sudah dipakai
        get_db().collection("discord_verify").document(data["discord_id"]).update({
            "used": True
        })
        return data
    return None


def mark_user_verified(discord_id: str, discord_name: str):
    """
    Simpan discordId dan discordName ke dokumen user di koleksi users.
    Field ini tidak bisa diubah setelah diset (pengecekan dilakukan di app).
    """
    get_db().collection("users").document(discord_id).set({
        "discordId"  : discord_id,
        "discordName": discord_name,
        "isVerified" : True,
    }, merge=True)


# ─────────────────────────────────────────────────────────────────
#  HELPER: SOAL AKTIF
# ─────────────────────────────────────────────────────────────────
def get_active_soal_tg(guild_id: str) -> tuple[str | None, dict | None]:
    """
    Ambil soal tebak gambar aktif untuk server ini.
    Cek guild spesifik dulu, kalau kosong cek soal global (guild_id == "").
    Returns (doc_id, data) atau (None, None).
    """
    for gid in [guild_id, ""]:
        docs = (
            get_db().collection("tebak_gambar")
            .where("guild_id", "==", gid)
            .where("status", "==", "active")
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.id, doc.to_dict()
    return None, None


def activate_next_soal_tg(guild_id: str) -> tuple[str | None, dict | None]:
    """
    Aktifkan soal berikutnya secara acak dengan prioritas:
    1. Soal approved baru (belum pernah tampil) → prioritas utama, acak
    2. Soal done (sudah pernah tampil) → putar ulang acak kalau pool habis
    Cek guild spesifik dulu, lalu soal global (guild_id == "").
    """
    db = get_db()

    # Ambil history soal yang sudah pernah aktif/done di server ini
    # dari tg_state supaya tidak perlu query besar
    state_ref = db.collection("tg_state").document(guild_id)
    state     = state_ref.get()
    shown_ids = state.to_dict().get("shown_ids", []) if state.exists else []

    # ── PRIORITAS 1: soal approved BARU (belum pernah tampil) ──
    new_candidates = []
    for gid in [guild_id, ""]:
        docs = (
            db.collection("tebak_gambar")
            .where("guild_id", "==", gid)
            .where("status", "==", "approved")
            .stream()
        )
        for doc in docs:
            if doc.id not in shown_ids:
                new_candidates.append((doc.id, doc.to_dict()))

    if new_candidates:
        doc_id, data = random.choice(new_candidates)
        db.collection("tebak_gambar").document(doc_id).update({
            "status"     : "active",
            "activatedAt": datetime.now(timezone.utc),
        })
        # Tambah ke shown_ids
        shown_ids.append(doc_id)
        state_ref.set({"shown_ids": shown_ids}, merge=True)
        data["status"] = "active"
        return doc_id, data

    # ── PRIORITAS 2: putar ulang dari soal done (reset shown_ids) ──
    repeat_candidates = []
    for gid in [guild_id, ""]:
        docs = (
            db.collection("tebak_gambar")
            .where("guild_id", "==", gid)
            .where("status", "==", "done")
            .stream()
        )
        for doc in docs:
            repeat_candidates.append((doc.id, doc.to_dict()))

    if repeat_candidates:
        doc_id, data = random.choice(repeat_candidates)
        # Reset soal terpilih jadi approved dulu lalu active
        db.collection("tebak_gambar").document(doc_id).update({
            "status"     : "active",
            "revealed"   : [],
            "solver"     : {},
            "activatedAt": datetime.now(timezone.utc),
        })
        # Reset shown_ids, mulai siklus baru hanya dengan soal ini
        state_ref.set({"shown_ids": [doc_id]}, merge=True)
        data["status"]   = "active"
        data["revealed"] = []
        return doc_id, data

    return None, None


def save_tg_message(guild_id: str, channel_id: int, message_id: int):
    """Simpan channel_id & message_id pesan soal terakhir per server."""
    get_db().collection("tg_state").document(guild_id).set({
        "channel_id": channel_id,
        "message_id": message_id,
    }, merge=True)


def get_tg_message(guild_id: str) -> tuple[int | None, int | None]:
    """Ambil channel_id & message_id pesan soal terakhir."""
    doc = get_db().collection("tg_state").document(guild_id).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("channel_id"), data.get("channel_id") and data.get("message_id")
    return None, None


# ─────────────────────────────────────────────────────────────────
#  HELPER: TAMPILAN TEBAKAN (GARIS BAWAH)
# ─────────────────────────────────────────────────────────────────
def mask_answer_tg(answer: str, revealed: list[int]) -> str:
    """
    Tampilkan jawaban dengan format garis bawah.
    Spasi antar kata tetap spasi, huruf tersembunyi jadi '_ '.
    Contoh: 'Nasi Goreng' → '_ _ _ _   _ _ _ _ _ _'
    """
    parts = []
    for i, ch in enumerate(answer):
        if ch == " ":
            parts.append("  ")      # spasi ganda sebagai pemisah kata
        elif i in revealed:
            parts.append(ch + " ")
        else:
            parts.append("_ ")
    return "".join(parts).strip()


def build_tg_display(soal: dict) -> str:
    """Format tampilan soal tebak gambar (tanpa gambar, gambar dikirim sebagai embed)."""
    answer    = soal.get("answer", "")
    revealed  = soal.get("revealed", [])
    submitter = soal.get("submitterName", "Anonim")
    hint      = soal.get("hint", "")        # opsional: hint dari pembuat soal

    total_letters   = len([c for c in answer if c != " "])
    revealed_count  = len(revealed)

    lines = [
        f"**from:** {submitter}",
        f"**A:** `{mask_answer_tg(answer, revealed)}`",
        f"📊 `{revealed_count}/{total_letters}` huruf terbuka",
    ]
    if hint:
        lines.append(f"💡 **Hint:** {hint}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────
#  HELPER: JAWABAN
# ─────────────────────────────────────────────────────────────────
def try_answer_tg(doc_id: str, soal: dict,
                  answer_input: str,
                  user_id: str, user_name: str) -> dict:
    """
    Cek jawaban penuh soal tebak gambar.
    Returns dict:
      correct   : bool
      reward    : int   (0 jika salah)
      completed : bool
    """
    answer = soal.get("answer", "")
    if answer_input.strip().lower() != answer.strip().lower():
        return {"correct": False, "reward": 0, "completed": False}

    reward = random.randint(REWARD_MIN, REWARD_MAX)

    # Buka semua huruf
    revealed = list(range(len(answer)))

    solver_entry = {
        "name"  : user_name,
        "earned": reward,
    }

    get_db().collection("tebak_gambar").document(doc_id).update({
        "status"  : "done",
        "revealed": revealed,
        "solver"  : solver_entry,
        "doneAt"  : datetime.now(timezone.utc),
    })

    return {"correct": True, "reward": reward, "completed": True}


# ─────────────────────────────────────────────────────────────────
#  HELPER: TG MEMBER
# ─────────────────────────────────────────────────────────────────
def is_tg_member(guild_id: str, user_id: str) -> bool:
    doc = get_db().collection("tg_members").document(f"{guild_id}_{user_id}").get()
    return doc.exists


def join_tg(guild_id: str, user_id: str):
    get_db().collection("tg_members").document(f"{guild_id}_{user_id}").set({
        "user_id" : user_id,
        "guild_id": guild_id,
        "joinedAt": datetime.now(timezone.utc),
    }, merge=True)
    # Simpan lastGuild ke users supaya app tahu server ini
    get_db().collection("users").document(user_id).set(
        {"lastGuild": guild_id}, merge=True
    )


# ─────────────────────────────────────────────────────────────────
#  VERIFIKASI SERVER (ADMIN PANEL)
# ─────────────────────────────────────────────────────────────────
def generate_server_verify_code(guild_id: str, guild_name: str,
                                 owner_id: str, owner_name: str) -> str:
    """
    Buat kode verifikasi server 32 karakter.
    Simpan ke Firestore koleksi server_verify.
    Returns kode yang dibuat.
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    code     = "".join(random.choices(alphabet, k=VERIFY_CODE_LEN))

    get_db().collection("server_verify").document(guild_id).set({
        "guild_id"  : guild_id,
        "guild_name": guild_name,
        "owner_id"  : owner_id,
        "owner_name": owner_name,
        "code"      : code,
        "createdAt" : datetime.now(timezone.utc),
        "used"      : False,
    })
    return code


def validate_server_verify_code(code: str) -> dict | None:
    """
    Cari kode verifikasi server.
    Returns data guild jika valid & belum kedaluwarsa, None jika tidak.
    """
    docs = (
        get_db().collection("server_verify")
        .where("code", "==", code)
        .where("used", "==", False)
        .limit(1)
        .stream()
    )
    for doc in docs:
        data    = doc.to_dict()
        created = data.get("createdAt")
        if created:
            if hasattr(created, "tzinfo") and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            if age_hours > VERIFY_TTL_HOURS:
                return None
        # Tandai sudah dipakai
        get_db().collection("server_verify").document(data["guild_id"]).update({
            "used": True
        })
        # Simpan data admin ke Firestore supaya app bisa cek
        get_db().collection("server_admins").document(data["owner_id"]).set({
            "guild_id"  : data["guild_id"],
            "guild_name": data["guild_name"],
            "owner_id"  : data["owner_id"],
            "owner_name": data["owner_name"],
            "verifiedAt": datetime.now(timezone.utc),
        }, merge=True)
        return data
    return None


# ─────────────────────────────────────────────────────────────────
#  APPROVE / REJECT SOAL (ADMIN PANEL)
# ─────────────────────────────────────────────────────────────────
def approve_soal(doc_id: str) -> bool:
    """Approve soal tebak gambar — ubah status jadi approved."""
    try:
        get_db().collection("tebak_gambar").document(doc_id).update({
            "status"    : "approved",
            "approvedAt": datetime.now(timezone.utc),
            "rejectedReason": "",
        })
        return True
    except Exception:
        return False


def reject_soal(doc_id: str, reason: str) -> bool:
    """Reject soal tebak gambar — ubah status jadi rejected + simpan alasan."""
    try:
        get_db().collection("tebak_gambar").document(doc_id).update({
            "status"        : "rejected",
            "rejectedAt"    : datetime.now(timezone.utc),
            "rejectedReason": reason,
        })
        return True
    except Exception:
        return False


def get_pending_soal(guild_id: str) -> list[dict]:
    """
    Ambil semua soal pending untuk server ini + soal global (guild_id == "").
    Returns list of {doc_id, ...data}
    """
    result = []
    for gid in [guild_id, ""]:
        docs = (
            get_db().collection("tebak_gambar")
            .where("guild_id", "==", gid)
            .where("status", "==", "pending")
            .order_by("createdAt")
            .stream()
        )
        for doc in docs:
            data = doc.to_dict()
            data["doc_id"] = doc.id
            result.append(data)
    return result


def get_soal_by_submitter(submitter_name: str) -> list[dict]:
    """
    Ambil semua soal yang disubmit oleh user tertentu.
    Returns list of {doc_id, ...data}
    """
    docs = (
        get_db().collection("tebak_gambar")
        .where("submitterName", "==", submitter_name)
        .order_by("createdAt")
        .stream()
    )
    result = []
    for doc in docs:
        data = doc.to_dict()
        data["doc_id"] = doc.id
        result.append(data)
    return result
