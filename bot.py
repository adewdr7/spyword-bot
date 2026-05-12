import discord
import os
import json
import random
import string
import asyncio
from discord.ext import commands
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta

# ═══════════════════════════════════════════
#  INISIALISASI FIREBASE
# ═══════════════════════════════════════════
firebase_key_json = os.environ.get("FIREBASE_KEY_JSON")
if firebase_key_json:
    cred_dict = json.loads(firebase_key_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
else:
    raise ValueError("FIREBASE_KEY_JSON tidak ditemukan di environment variables!")

db = firestore.client()

import coins as coin_sys
import quiz as quiz_sys
import tebak_gambar as tg_sys

# ═══════════════════════════════════════════
#  INISIALISASI BOT DISCORD
# ═══════════════════════════════════════════
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ═══════════════════════════════════════════
#  DATA KATA BUILT-IN (sama dengan aplikasi)
# ═══════════════════════════════════════════
BUILT_IN_WORDS = [
    {"civilianWord": "Kucing", "spyWord": "Anjing", "category": "Hewan"},
    {"civilianWord": "Pizza", "spyWord": "Burger", "category": "Makanan"},
    {"civilianWord": "Sepeda", "spyWord": "Motor", "category": "Kendaraan"},
    {"civilianWord": "Dokter", "spyWord": "Perawat", "category": "Profesi"},
    {"civilianWord": "Pantai", "spyWord": "Gunung", "category": "Wisata Alam"},
    {"civilianWord": "Facebook", "spyWord": "Instagram", "category": "Media Sosial"},
    {"civilianWord": "Kopi", "spyWord": "Teh", "category": "Minuman"},
    {"civilianWord": "Futsal", "spyWord": "Basket", "category": "Olahraga"},
    {"civilianWord": "Batman", "spyWord": "Superman", "category": "Superhero"},
    {"civilianWord": "Nasi Goreng", "spyWord": "Mie Goreng", "category": "Masakan"},
    {"civilianWord": "Gitar", "spyWord": "Piano", "category": "Alat Musik"},
    {"civilianWord": "Singa", "spyWord": "Harimau", "category": "Hewan Buas"},
    {"civilianWord": "Apel", "spyWord": "Mangga", "category": "Buah"},
    {"civilianWord": "Buku", "spyWord": "Majalah", "category": "Bacaan"},
    {"civilianWord": "Laptop", "spyWord": "Tablet", "category": "Gadget"},
    {"civilianWord": "Kapal", "spyWord": "Pesawat", "category": "Transportasi"},
    {"civilianWord": "Bola", "spyWord": "Raket", "category": "Peralatan Olahraga"},
    {"civilianWord": "Coklat", "spyWord": "Permen", "category": "Makanan Manis"},
    {"civilianWord": "Hujan", "spyWord": "Salju", "category": "Cuaca"},
    {"civilianWord": "Tiktok", "spyWord": "Youtube", "category": "Platform Video"},
    {"civilianWord": "Indomie", "spyWord": "Pop Mie", "category": "Mie Instan"},
    {"civilianWord": "Warung", "spyWord": "Restoran", "category": "Tempat Makan"},
    {"civilianWord": "Tidur", "spyWord": "Istirahat", "category": "Aktivitas"},
    {"civilianWord": "Polisi", "spyWord": "Tentara", "category": "Aparat"},
    {"civilianWord": "Masjid", "spyWord": "Gereja", "category": "Tempat Ibadah"},
    {"civilianWord": "Jeruk", "spyWord": "Lemon", "category": "Buah Asam"},
    {"civilianWord": "Kuah", "spyWord": "Saus", "category": "Pelengkap Masakan"},
]

# ═══════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════
def generate_room_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(chars, k=6))

def get_next_word_pair(room_doc):
    used_keys = room_doc.get("usedWordPairs", [])
    custom_raw = room_doc.get("customWords", [])
    custom_pairs = [
        w for w in custom_raw
        if w.get("civilianWord") and w.get("spyWord")
    ]

    used_set = set(used_keys)

    available_custom = [
        w for w in custom_pairs
        if f"{w['civilianWord']}|{w['spyWord']}" not in used_set
    ]
    available_builtin = [
        w for w in BUILT_IN_WORDS
        if f"{w['civilianWord']}|{w['spyWord']}" not in used_set
    ]

    if available_custom and available_builtin:
        chosen = random.choice(available_custom) if random.randint(1, 10) <= 9 else random.choice(available_builtin)
    elif available_custom:
        chosen = random.choice(available_custom)
    elif available_builtin:
        chosen = random.choice(available_builtin)
    else:
        # Reset pool
        all_pairs = custom_pairs + BUILT_IN_WORDS
        chosen = random.choice(all_pairs)
        used_keys = []

    chosen_key = f"{chosen['civilianWord']}|{chosen['spyWord']}"
    if chosen_key not in used_keys:
        used_keys.append(chosen_key)

    return chosen, used_keys

async def send_dm(user, message):
    try:
        await user.send(message)
        return True
    except:
        return False

def get_player_mention(discord_name, guild):
    for member in guild.members:
        if member.name == discord_name or str(member) == discord_name:
            return member.mention
    return discord_name

# ═══════════════════════════════════════════
#  EVENTS
# ═══════════════════════════════════════════
@bot.event
async def on_ready():
    print(f"✅ {bot.user} sudah online!")
    await bot.change_presence(activity=discord.Game(name="SpyWord 🕵️ | !help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    import traceback
    print(f"❌ ERROR pada command '{ctx.command}': {error}")
    traceback.print_exc()
    await ctx.send(f"❌ Error: {error}")

# ═══════════════════════════════════════════
#  COMMAND: !help
# ═══════════════════════════════════════════
@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(
        title="🕵️ SpyWord Bot - Bantuan",
        description="Game tebak-tebakan kata! Temukan siapa Spy-nya!",
        color=0x6C5CE7
    )
    embed.add_field(
        name="📋 Command",
        value=(
            "`!buat` — Buat room baru\n"
            "`!join KODE` — Join room\n"
            "`!siap` — Toggle siap/belum siap\n"
            "`!pemain` — Lihat daftar pemain\n"
            "`!setting spy 2/3` — Set jumlah spy (host)\n"
            "`!setting mode normal/hard` — Set mode (host)\n"
            "`!tambahkata [warga] | [spy] | [kategori]` — Tambah kata custom (host)\n"
            "`!mulai` — Mulai game (host, semua harus siap)\n"
            "`!kataku` — Lihat kata rahasiamu via DM\n"
            "`!vote @nama` — Vote siapa yang spy\n"
            "`!hasilvote` — Lihat hasil vote saat ini\n"
            "`!lagi` — Main lagi (host, di result)\n"
            "`!keluar` — Keluar dari room\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🎮 Cara Main SpyWord",
        value=(
            "1. Host ketik `!buat` untuk buat room\n"
            "2. Teman join pakai `!join KODE`\n"
            "3. Semua ketik `!siap`\n"
            "4. Host ketik `!mulai`\n"
            "5. Cek kata rahasia via DM\n"
            "6. Diskusi & vote spy!\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🧩 Quiz Tebak Kata",
        value=(
            "`!qjoin` — Bergabung ke quiz\n"
            "`!soal` — Tampilkan soal aktif (gratis)\n"
            "`!clue` — Buka 1 huruf acak (6 koin)\n"
            "`!f[n] [huruf]` — Tebak huruf posisi n (contoh: `!f1 J`)\n"
            "`!j [jawaban]` — Tebak jawaban langsung (contoh: `!j Jakarta`)\n"
            "`!kirimsoal` — Submit soal baru via DM bot (22 koin)\n"
        ),
        inline=False
    )
    embed.add_field(
        name="💰 Sistem Koin",
        value=(
            "`!koin` — Cek saldo koin\n"
            "`!claim` — Klaim koin harian (66-110 koin, per 24 jam)\n"
        ),
        inline=False
    )
    embed.add_field(
        name="🖼️ Tebak Gambar",
        value=(
            "`!tgjoin` — Bergabung ke tebak gambar\n"
            "`!tg` — Tampilkan soal tebak gambar aktif\n"
            "`!jg [jawaban]` — Jawab soal tebak gambar\n"
            "`!v` — Generate kode verifikasi Discord (via DM bot)\n"
        ),
        inline=False
    )
    embed.set_footer(text="SpyWordBot • Game Chat Indonesia")
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !buat
# ═══════════════════════════════════════════
@bot.command(name="buat")
async def buat_room(ctx):
    player_name = str(ctx.author)
    
    # Cek apakah sudah di room lain
    rooms = db.collection("rooms").where("status", "in", ["waiting", "playing"]).stream()
    for room in rooms:
        players_ref = db.collection("rooms").document(room.id).collection("players").document(player_name).get()
        if players_ref.exists:
            await ctx.send(f"❌ {ctx.author.mention} kamu sudah ada di room **{room.id}**! Ketik `!keluar` dulu.")
            return

    room_code = generate_room_code()
    room_data = {
        "code": room_code,
        "host": player_name,
        "status": "waiting",
        "spyCount": 2,
        "mode": "NORMAL",
        "usedWordPairs": [],
        "customWords": [],
        "createdAt": firestore.SERVER_TIMESTAMP,
        "lastActive": firestore.SERVER_TIMESTAMP,
        "platform": "discord"
    }

    db.collection("rooms").document(room_code).set(room_data)

    player_data = {
        "name": player_name,
        "ready": False,
        "isHost": True,
        "role": "",
        "word": "",
        "votedFor": "",
        "joinedAt": firestore.SERVER_TIMESTAMP,
        "platform": "discord",
        "discordId": str(ctx.author.id)
    }
    db.collection("rooms").document(room_code).collection("players").document(player_name).set(player_data)

    embed = discord.Embed(
        title="🎮 Room SpyWord Dibuat!",
        color=0x00B894
    )
    embed.add_field(name="🔑 Kode Room", value=f"```{room_code}```", inline=False)
    embed.add_field(name="👑 Host", value=ctx.author.mention, inline=True)
    embed.add_field(name="👥 Pemain", value="1 orang", inline=True)
    embed.add_field(name="⚙️ Setting", value="2 Spy | Mode Normal", inline=False)
    embed.add_field(
        name="📢 Cara Join",
        value=f"Teman ketik: `!join {room_code}`",
        inline=False
    )
    embed.set_footer(text="Ketik !siap kalau sudah siap, lalu host ketik !mulai")
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !join
# ═══════════════════════════════════════════
@bot.command(name="join")
async def join_room(ctx, code: str = None):
    if not code:
        await ctx.send("❌ Format: `!join KODROOM`")
        return

    code = code.upper()
    player_name = str(ctx.author)

    room_ref = db.collection("rooms").document(code).get()
    if not room_ref.exists:
        await ctx.send(f"❌ Room **{code}** tidak ditemukan!")
        return

    room_data = room_ref.to_dict()
    if room_data.get("status") != "waiting":
        await ctx.send(f"❌ Game di room **{code}** sudah dimulai!")
        return

    # Cek apakah sudah ada di room ini
    existing = db.collection("rooms").document(code).collection("players").document(player_name).get()
    if existing.exists:
        await ctx.send(f"❌ {ctx.author.mention} kamu sudah ada di room ini!")
        return

    player_data = {
        "name": player_name,
        "ready": False,
        "isHost": False,
        "role": "",
        "word": "",
        "votedFor": "",
        "joinedAt": firestore.SERVER_TIMESTAMP,
        "platform": "discord",
        "discordId": str(ctx.author.id)
    }
    db.collection("rooms").document(code).collection("players").document(player_name).set(player_data)
    db.collection("rooms").document(code).update({"lastActive": firestore.SERVER_TIMESTAMP})

    players = db.collection("rooms").document(code).collection("players").stream()
    player_count = sum(1 for _ in players)

    embed = discord.Embed(
        title="✅ Berhasil Join Room!",
        color=0x00B894
    )
    embed.add_field(name="🔑 Kode Room", value=f"`{code}`", inline=True)
    embed.add_field(name="👥 Pemain", value=f"{player_count} orang", inline=True)
    embed.set_footer(text="Ketik !siap kalau sudah siap!")
    await ctx.send(f"{ctx.author.mention} bergabung ke room **{code}**!", embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !siap
# ═══════════════════════════════════════════
@bot.command(name="siap")
async def toggle_ready(ctx):
    player_name = str(ctx.author)
    room_code, _ = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    player_ref = db.collection("rooms").document(room_code).collection("players").document(player_name)
    player_data = player_ref.get().to_dict()
    current_ready = player_data.get("ready", False)
    new_ready = not current_ready

    player_ref.update({"ready": new_ready})

    if new_ready:
        await ctx.send(f"✅ {ctx.author.mention} **SIAP!** di room `{room_code}`")
    else:
        await ctx.send(f"⏳ {ctx.author.mention} **Belum Siap** di room `{room_code}`")

# ═══════════════════════════════════════════
#  COMMAND: !pemain
# ═══════════════════════════════════════════
@bot.command(name="pemain")
async def list_players(ctx):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    players = db.collection("rooms").document(room_code).collection("players").stream()
    player_list = [p.to_dict() for p in players]

    embed = discord.Embed(
        title=f"👥 Pemain di Room {room_code}",
        color=0x6C5CE7
    )

    lines = []
    for p in player_list:
        name = p.get("name", "")
        ready = p.get("ready", False)
        is_host = p.get("isHost", False)
        platform = p.get("platform", "android")
        
        status = "✅" if ready else "⏳"
        host_tag = " 👑" if is_host else ""
        platform_tag = " 📱" if platform == "android" else " 💻"
        lines.append(f"{status} {name}{host_tag}{platform_tag}")

    embed.add_field(name="Daftar Pemain", value="\n".join(lines) if lines else "Kosong", inline=False)
    embed.add_field(name="⚙️ Setting", value=f"{room_data.get('spyCount', 2)} Spy | Mode {room_data.get('mode', 'NORMAL')}", inline=False)
    embed.set_footer(text="✅ Siap | ⏳ Belum | 👑 Host | 📱 Android | 💻 Discord")
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !setting
# ═══════════════════════════════════════════
@bot.command(name="setting")
async def setting(ctx, tipe: str = None, nilai: str = None):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    if room_data.get("host") != player_name:
        await ctx.send(f"❌ Hanya host yang bisa ubah setting!")
        return

    if room_data.get("status") != "waiting":
        await ctx.send(f"❌ Tidak bisa ubah setting saat game berlangsung!")
        return

    if tipe == "spy":
        if nilai not in ["2", "3"]:
            await ctx.send("❌ Format: `!setting spy 2` atau `!setting spy 3`")
            return
        db.collection("rooms").document(room_code).update({"spyCount": int(nilai)})
        await ctx.send(f"✅ Jumlah spy diubah ke **{nilai}**!")

    elif tipe == "mode":
        if nilai and nilai.upper() in ["NORMAL", "HARD"]:
            db.collection("rooms").document(room_code).update({"mode": nilai.upper()})
            await ctx.send(f"✅ Mode diubah ke **{nilai.upper()}**!")
        else:
            await ctx.send("❌ Format: `!setting mode normal` atau `!setting mode hard`")
    else:
        await ctx.send("❌ Format: `!setting spy 2/3` atau `!setting mode normal/hard`")

# ═══════════════════════════════════════════
#  COMMAND: !tambahkata
# ═══════════════════════════════════════════
@bot.command(name="tambahkata")
async def tambah_kata(ctx, *, args: str = None):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    if room_data.get("host") != player_name:
        await ctx.send(f"❌ Hanya host yang bisa tambah kata!")
        return

    if not args or "|" not in args:
        await ctx.send("❌ Format: `!tambahkata [kata warga] | [kata spy] | [kategori]`\nContoh: `!tambahkata Apel | Jeruk | Buah`")
        return

    parts = [p.strip() for p in args.split("|")]
    if len(parts) < 2:
        await ctx.send("❌ Format: `!tambahkata [kata warga] | [kata spy] | [kategori]`")
        return

    civilian_word = parts[0]
    spy_word = parts[1]
    category = parts[2] if len(parts) > 2 else "Custom"

    new_word = {
        "civilianWord": civilian_word,
        "spyWord": spy_word,
        "category": category
    }

    custom_words = room_data.get("customWords", [])
    custom_words.append(new_word)
    db.collection("rooms").document(room_code).update({"customWords": custom_words})

    await ctx.send(f"✅ Kata **\"{civilian_word} vs {spy_word}\"** (📂 {category}) berhasil ditambahkan!")

# ═══════════════════════════════════════════
#  COMMAND: !mulai
# ═══════════════════════════════════════════
@bot.command(name="mulai")
async def mulai_game(ctx):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    if room_data.get("host") != player_name:
        await ctx.send(f"❌ Hanya host yang bisa mulai game!")
        return

    if room_data.get("status") != "waiting":
        await ctx.send(f"❌ Game sudah berjalan!")
        return

    players_snap = list(db.collection("rooms").document(room_code).collection("players").stream())
    players = [p.to_dict() for p in players_snap]

    if len(players) < 3:
        await ctx.send(f"❌ Minimal **3 pemain** untuk mulai game! Sekarang: {len(players)} orang.")
        return

    not_ready = [p["name"] for p in players if not p.get("ready", False)]
    if not_ready:
        await ctx.send(f"❌ Pemain berikut belum siap: **{', '.join(not_ready)}**\nSemua harus ketik `!siap` dulu!")
        return

    # Pilih kata
    word_pair, used_keys = get_next_word_pair(room_data)

    # Assign role
    spy_count = room_data.get("spyCount", 2)
    shuffled = players.copy()
    random.shuffle(shuffled)
    spies = {p["name"] for p in shuffled[:spy_count]}

    batch_data = {}
    for player in players:
        is_spy = player["name"] in spies
        batch_data[player["name"]] = {
            "role": "SPY" if is_spy else "CIVILIAN",
            "word": word_pair["spyWord"] if is_spy else word_pair["civilianWord"],
            "votedFor": ""
        }

    # Update Firestore
    for player in players:
        db.collection("rooms").document(room_code).collection("players").document(player["name"]).update(batch_data[player["name"]])

    game_mode = room_data.get("mode", "NORMAL")
    db.collection("rooms").document(room_code).update({
        "status": "playing",
        "currentWordPair": f"{word_pair['civilianWord']}|{word_pair['spyWord']}",
        "category": word_pair.get("category", ""),
        "mode": game_mode,
        "votePhase": False,
        "readyForVote": [],
        "usedWordPairs": used_keys
    })

    # Kirim DM ke semua pemain Discord
    dm_failed = []
    for player in players:
        discord_id = player.get("discordId")
        if discord_id:
            try:
                member = await bot.fetch_user(int(discord_id))
                role = batch_data[player["name"]]["role"]
                word = batch_data[player["name"]]["word"]
                
                if role == "SPY":
                    role_emoji = "🕵️"
                    role_text = "**SPY**"
                    color_hint = "Kamu adalah Spy! Sembunyikan identitasmu!"
                else:
                    role_emoji = "👤"
                    role_text = "**CIVILIAN**"
                    color_hint = "Kamu adalah Warga! Temukan siapa Spy-nya!"

                dm_msg = (
                    f"{role_emoji} **Role kamu:** {role_text}\n"
                    f"🔤 **Kata kamu:** `{word}`\n"
                )
                if game_mode == "NORMAL" and word_pair.get("category"):
                    dm_msg += f"📂 **Kategori:** {word_pair['category']}\n"
                dm_msg += f"\n_{color_hint}_"

                await member.send(dm_msg)
            except Exception as e:
                dm_failed.append(player["name"])

    # Announce di channel
    embed = discord.Embed(
        title="🎮 Game SpyWord Dimulai!",
        description=f"Room: `{room_code}` | {len(players)} pemain",
        color=0xE17055
    )
    embed.add_field(
        name="📊 Info Game",
        value=(
            f"🕵️ Jumlah Spy: **{spy_count}**\n"
            f"⚙️ Mode: **{game_mode}**\n"
            f"{'📂 Kategori: **' + word_pair['category'] + '**' if game_mode == 'NORMAL' else '🔒 Mode Hard: Tanpa kategori!'}"
        ),
        inline=False
    )
    embed.add_field(
        name="📱 Pemain Android",
        value="Cek kata rahasiamu di aplikasi!",
        inline=False
    )
    embed.add_field(
        name="💻 Pemain Discord",
        value="Cek DM dari bot untuk kata rahasiamu!\nKetik `!kataku` kalau DM tidak masuk.",
        inline=False
    )
    embed.add_field(
        name="🗳️ Cara Vote",
        value="Setelah diskusi, ketik `!vote @nama` untuk vote!\nLihat hasil vote: `!hasilvote`",
        inline=False
    )
    embed.set_footer(text="Selamat bermain! 🕵️")
    await ctx.send(embed=embed)

    if dm_failed:
        await ctx.send(f"⚠️ DM gagal dikirim ke: **{', '.join(dm_failed)}**\nMereka bisa ketik `!kataku` untuk lihat kata.")

# ═══════════════════════════════════════════
#  COMMAND: !kataku
# ═══════════════════════════════════════════
@bot.command(name="kataku")
async def kata_ku(ctx):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    if room_data.get("status") != "playing":
        await ctx.send(f"❌ Game belum dimulai!")
        return

    player_ref = db.collection("rooms").document(room_code).collection("players").document(player_name).get()
    player_data = player_ref.to_dict()

    role = player_data.get("role", "")
    word = player_data.get("word", "")
    game_mode = room_data.get("mode", "NORMAL")
    category = room_data.get("category", "")

    if not role:
        await ctx.send(f"❌ Data role tidak ditemukan!")
        return

    if role == "SPY":
        role_emoji = "🕵️"
        role_text = "**SPY**"
        hint = "Kamu adalah Spy! Sembunyikan identitasmu!"
    else:
        role_emoji = "👤"
        role_text = "**CIVILIAN**"
        hint = "Kamu adalah Warga! Temukan siapa Spy-nya!"

    dm_msg = (
        f"{role_emoji} **Role kamu:** {role_text}\n"
        f"🔤 **Kata kamu:** `{word}`\n"
    )
    if game_mode == "NORMAL" and category:
        dm_msg += f"📂 **Kategori:** {category}\n"
    dm_msg += f"\n_{hint}_"

    try:
        await ctx.author.send(dm_msg)
        await ctx.send(f"✅ {ctx.author.mention} cek DM kamu!")
    except:
        await ctx.send(f"❌ Tidak bisa kirim DM! Aktifkan DM dari server ini dulu.")

# ═══════════════════════════════════════════
#  COMMAND: !vote
# ═══════════════════════════════════════════
@bot.command(name="vote")
async def vote(ctx, target: discord.Member = None):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    if room_data.get("status") != "playing":
        await ctx.send(f"❌ Game belum dimulai!")
        return

    if not target:
        await ctx.send("❌ Format: `!vote @nama`")
        return

    target_name = str(target)
    if target_name == player_name:
        await ctx.send(f"❌ Tidak bisa vote diri sendiri!")
        return

    # Cek target ada di room
    target_ref = db.collection("rooms").document(room_code).collection("players").document(target_name).get()
    if not target_ref.exists:
        await ctx.send(f"❌ **{target_name}** tidak ada di room ini!")
        return

    # Cek sudah vote belum
    player_ref = db.collection("rooms").document(room_code).collection("players").document(player_name).get()
    player_data = player_ref.to_dict()
    if player_data.get("votedFor"):
        await ctx.send(f"❌ {ctx.author.mention} kamu sudah vote **{player_data['votedFor']}**!")
        return

    # Simpan vote
    db.collection("rooms").document(room_code).collection("players").document(player_name).update({
        "votedFor": target_name
    })

    await ctx.send(f"🗳️ {ctx.author.mention} vote untuk **{target_name}**!")

    # Cek apakah semua sudah vote
    await asyncio.sleep(1)
    await check_vote_complete(ctx, room_code)

async def check_vote_complete(ctx, room_code):
    players_snap = list(db.collection("rooms").document(room_code).collection("players").stream())
    players = [p.to_dict() for p in players_snap]

    total = len(players)
    voted = sum(1 for p in players if p.get("votedFor"))

    if voted >= total:
        await determine_result(ctx, room_code, players)

async def determine_result(ctx, room_code, players):
    vote_counts = {}
    for p in players:
        voted_for = p.get("votedFor", "")
        if voted_for:
            vote_counts[voted_for] = vote_counts.get(voted_for, 0) + 1

    most_voted = max(vote_counts, key=vote_counts.get) if vote_counts else ""
    voted_player = next((p for p in players if p.get("name") == most_voted), None)
    voted_role = voted_player.get("role", "") if voted_player else ""

    winner = "CIVILIANS" if voted_role == "SPY" else "SPIES"

    db.collection("rooms").document(room_code).update({
        "status": "result",
        "mostVoted": most_voted,
        "winner": winner
    })

    # Tampilkan hasil
    embed = discord.Embed(
        title="🏁 Hasil Voting!",
        color=0x00B894 if winner == "CIVILIANS" else 0xD63031
    )

    if winner == "CIVILIANS":
        embed.description = "🎉 **WARGA MENANG!** Spy berhasil ditemukan!"
    else:
        embed.description = "🕵️ **SPY MENANG!** Spy berhasil menipu semua orang!"

    embed.add_field(name="🗳️ Paling Banyak Divote", value=most_voted if most_voted else "Tidak ada", inline=True)
    embed.add_field(name="🎭 Role-nya", value=voted_role if voted_role else "?", inline=True)

    # Tampilkan semua role
    reveal_lines = []
    for p in players:
        name = p.get("name", "")
        role = p.get("role", "")
        word = p.get("word", "")
        emoji = "🕵️" if role == "SPY" else "👤"
        reveal_lines.append(f"{emoji} **{name}** — {role} | Kata: `{word}`")

    embed.add_field(name="📋 Semua Role & Kata", value="\n".join(reveal_lines), inline=False)
    embed.add_field(name="🔄 Main Lagi?", value="Host ketik `!lagi` untuk main lagi!", inline=False)
    embed.set_footer(text="Ketik !keluar untuk keluar dari room")

    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !hasilvote
# ═══════════════════════════════════════════
@bot.command(name="hasilvote")
async def hasil_vote(ctx):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    players_snap = list(db.collection("rooms").document(room_code).collection("players").stream())
    players = [p.to_dict() for p in players_snap]

    vote_counts = {}
    voted_names = []
    for p in players:
        voted_for = p.get("votedFor", "")
        if voted_for:
            vote_counts[voted_for] = vote_counts.get(voted_for, 0) + 1
            voted_names.append(p.get("name"))

    total = len(players)
    voted = len(voted_names)

    embed = discord.Embed(
        title=f"🗳️ Hasil Vote Sementara — Room {room_code}",
        color=0x6C5CE7
    )
    embed.add_field(name="📊 Progress", value=f"{voted}/{total} sudah vote", inline=False)

    if vote_counts:
        lines = []
        for name, count in sorted(vote_counts.items(), key=lambda x: -x[1]):
            lines.append(f"**{name}** — {count} vote")
        embed.add_field(name="📋 Vote", value="\n".join(lines), inline=False)
    else:
        embed.add_field(name="📋 Vote", value="Belum ada yang vote", inline=False)

    belum_vote = [p.get("name") for p in players if not p.get("votedFor")]
    if belum_vote:
        embed.add_field(name="⏳ Belum Vote", value=", ".join(belum_vote), inline=False)

    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !lagi
# ═══════════════════════════════════════════
@bot.command(name="lagi")
async def main_lagi(ctx):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    if room_data.get("host") != player_name:
        await ctx.send(f"❌ Hanya host yang bisa reset game!")
        return

    if room_data.get("status") != "result":
        await ctx.send(f"❌ Game belum selesai!")
        return

    players_snap = list(db.collection("rooms").document(room_code).collection("players").stream())

    # Reset semua player
    for p in players_snap:
        db.collection("rooms").document(room_code).collection("players").document(p.id).update({
            "ready": False,
            "role": "",
            "word": "",
            "votedFor": ""
        })

    # Reset room
    db.collection("rooms").document(room_code).update({
        "status": "waiting",
        "votePhase": False,
        "readyForVote": [],
        "mostVoted": "",
        "winner": "",
        "currentWordPair": "",
        "category": ""
    })

    embed = discord.Embed(
        title="🔄 Room Direset!",
        description=f"Room `{room_code}` siap untuk ronde baru!",
        color=0x00B894
    )
    embed.add_field(name="📢 Selanjutnya", value="Semua ketik `!siap`, lalu host ketik `!mulai`!", inline=False)
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !keluar
# ═══════════════════════════════════════════
@bot.command(name="keluar")
async def keluar_room(ctx):
    player_name = str(ctx.author)
    room_code, room_data = find_player_room(player_name)

    if not room_code:
        await ctx.send(f"❌ {ctx.author.mention} kamu tidak ada di room manapun!")
        return

    db.collection("rooms").document(room_code).collection("players").document(player_name).delete()

    # Cek apakah room kosong
    remaining = list(db.collection("rooms").document(room_code).collection("players").stream())
    if not remaining:
        db.collection("rooms").document(room_code).delete()
        await ctx.send(f"👋 {ctx.author.mention} keluar. Room `{room_code}` dihapus karena kosong.")
    else:
        await ctx.send(f"👋 {ctx.author.mention} keluar dari room `{room_code}`.")

# ═══════════════════════════════════════════
#  HELPER: Cari room player
# ═══════════════════════════════════════════
def find_player_room(player_name):
    rooms = db.collection("rooms").where("status", "in", ["waiting", "playing", "result"]).stream()
    for room in rooms:
        player_ref = db.collection("rooms").document(room.id).collection("players").document(player_name).get()
        if player_ref.exists:
            return room.id, room.to_dict()
    return None, None

# ═══════════════════════════════════════════
#  COMMAND: !koin
# ═══════════════════════════════════════════
@bot.command(name="koin")
async def cek_koin(ctx):
    user_id = str(ctx.author.id)
    data = coin_sys.get_user_coins(user_id)
    balance = data.get("coins", 0)
    embed = discord.Embed(title="💰 Saldo Koin", color=0xFDCB6E)
    embed.add_field(name="👤 User", value=ctx.author.mention, inline=True)
    embed.add_field(name="💰 Koin", value=f"**{balance}** koin", inline=True)
    embed.set_footer(text="Ketik !claim untuk klaim koin harian")
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !claim
# ═══════════════════════════════════════════
@bot.command(name="claim")
async def claim_koin(ctx):
    user_id = str(ctx.author.id)
    success, gained, new_balance = coin_sys.do_claim(user_id)
    if success:
        embed = discord.Embed(
            title="🎁 Koin Harian Berhasil Diklaim!",
            color=0x00B894
        )
        embed.add_field(name="✨ Dapat", value=f"**+{gained}** koin", inline=True)
        embed.add_field(name="💰 Total", value=f"**{new_balance}** koin", inline=True)
        embed.set_footer(text="Kamu bisa claim lagi 24 jam kemudian")
    else:
        _, sisa = coin_sys.can_claim(user_id)
        embed = discord.Embed(
            title="⏳ Belum Bisa Claim",
            description=f"Coba lagi dalam **{coin_sys.format_seconds(sisa)}**",
            color=0xD63031
        )
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !qjoin
# ═══════════════════════════════════════════
@bot.command(name="qjoin")
async def quiz_join(ctx):
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id)

    # Simpan lastGuild & tandai user sudah join quiz di server ini
    quiz_sys.get_db().collection("users").document(user_id).set(
        {"lastGuild": guild_id}, merge=True
    )
    quiz_sys.get_db().collection("quiz_members").document(f"{guild_id}_{user_id}").set({
        "user_id": user_id,
        "guild_id": guild_id,
    }, merge=True)

    data = coin_sys.get_user_coins(user_id)
    balance = data.get("coins", 0)
    embed = discord.Embed(
        title="🎮 Bergabung ke Quiz!",
        description=f"{ctx.author.mention} siap bermain quiz!",
        color=0x6C5CE7
    )
    embed.add_field(name="💰 Saldo Koin", value=f"**{balance}** koin", inline=True)
    embed.add_field(
        name="📋 Command Quiz",
        value=(
            "`!soal` — Tampilkan soal aktif (gratis)\n"
            "`!clue` — Buka 1 huruf acak (6 koin)\n"
            "`!f[n] [huruf]` — Tebak huruf di posisi n\n"
            "`!j [jawaban]` — Tebak jawaban langsung\n"
            "`!claim` — Klaim koin harian\n"
            "`!kirimsoal` — Submit soal baru via DM (22 koin)\n"
        ),
        inline=False
    )
    embed.set_footer(text="Gunakan !claim dulu kalau koin belum cukup!")
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  HELPER: Build embed soal (reusable)
# ═══════════════════════════════════════════
def build_soal_embed(soal: dict) -> discord.Embed:
    answer = soal.get("answer", "")
    total_letters = len([c for c in answer if c != " "])
    revealed_count = len(soal.get("revealed", []))
    embed = discord.Embed(title="❓ Soal Quiz", color=0x74B9FF)
    embed.description = quiz_sys.build_display(soal)
    embed.add_field(
        name="📊 Progress",
        value=f"{revealed_count}/{total_letters} huruf terbuka",
        inline=True
    )
    embed.set_footer(text="!f[n] [huruf] tebak huruf • !j [jawaban] tebak penuh • !clue buka huruf (6 koin)")
    return embed

# ═══════════════════════════════════════════
#  HELPER: Cek apakah user sudah !qjoin
# ═══════════════════════════════════════════
def is_quiz_member(guild_id: str, user_id: str) -> bool:
    doc = quiz_sys.get_db().collection("quiz_members").document(f"{guild_id}_{user_id}").get()
    return doc.exists

# ═══════════════════════════════════════════
#  COMMAND: !soal
# ═══════════════════════════════════════════
@bot.command(name="soal")
async def tampil_soal(ctx):
    user_id  = str(ctx.author.id)
    guild_id = str(ctx.guild.id)

    if not is_quiz_member(guild_id, user_id):
        await ctx.send(f"❌ {ctx.author.mention} kamu belum join quiz! Ketik `!qjoin` dulu.")
        return

    doc_id, soal = quiz_sys.get_active_soal(guild_id)
    if not soal:
        # Coba aktifkan dari pool
        doc_id, soal = quiz_sys.activate_next_soal(guild_id)

    if not soal:
        await ctx.send(
            f"📭 {ctx.author.mention} belum ada soal aktif di server ini!\n"
            f"Submit soal dengan `!kirimsoal` via DM bot."
        )
        return

    # Auto reveal sesuai max_show
    revealed = soal.get("revealed", [])
    max_show = soal.get("max_show", 1)
    if len(revealed) < max_show:
        soal = quiz_sys.reveal_random_letter(doc_id, soal, max_show - len(revealed))

    embed = build_soal_embed(soal)
    msg = await ctx.send(embed=embed)
    # Simpan message ID supaya bisa diedit oleh !clue dan !f
    quiz_sys.save_soal_message(guild_id, ctx.channel.id, msg.id)

# ═══════════════════════════════════════════
#  COMMAND: !clue
# ═══════════════════════════════════════════
@bot.command(name="clue")
async def beli_clue(ctx):
    user_id  = str(ctx.author.id)
    guild_id = str(ctx.guild.id)

    if not is_quiz_member(guild_id, user_id):
        await ctx.send(f"❌ {ctx.author.mention} kamu belum join quiz! Ketik `!qjoin` dulu.")
        return

    doc_id, soal = quiz_sys.get_active_soal(guild_id)
    if not soal:
        await ctx.send(f"❌ {ctx.author.mention} tidak ada soal aktif saat ini!")
        return

    answer   = soal.get("answer", "")
    revealed = soal.get("revealed", [])
    hidden   = [i for i, c in enumerate(answer) if c != " " and i not in revealed]
    if not hidden:
        await ctx.send(f"❌ Semua huruf sudah terbuka!")
        return

    ok, new_bal = coin_sys.deduct_coins(user_id, quiz_sys.COST_CLUE)
    if not ok:
        data = coin_sys.get_user_coins(user_id)
        await ctx.send(
            f"❌ {ctx.author.mention} koin tidak cukup! "
            f"Kamu punya **{data.get('coins',0)}** koin, butuh **{quiz_sys.COST_CLUE}** koin."
        )
        return

    soal = quiz_sys.reveal_random_letter(doc_id, soal, 1)

    # Coba edit pesan soal sebelumnya
    channel_id, message_id = quiz_sys.get_soal_message(guild_id)
    embed = build_soal_embed(soal)
    embed.title = "❓ Soal Quiz (Clue dibuka!)"
    embed.color = 0xFDCB6E
    edited = False
    if channel_id and message_id:
        try:
            ch = bot.get_channel(int(channel_id))
            if ch:
                old_msg = await ch.fetch_message(int(message_id))
                await old_msg.edit(embed=embed)
                edited = True
                await ctx.message.add_reaction("✅")
        except:
            pass
    if not edited:
        msg = await ctx.send(embed=embed)
        quiz_sys.save_soal_message(guild_id, ctx.channel.id, msg.id)

# ═══════════════════════════════════════════
#  COMMAND: !f[n] [huruf]  (misal !f1 J)
# ═══════════════════════════════════════════
@bot.command(name="f")
async def fill_huruf(ctx, *, args: str = None):
    await ctx.send("❌ Format yang benar: `!f1 J` (angka langsung setelah f, lalu spasi, lalu huruf)")

@bot.listen("on_message")
async def on_fill_message(message):
    if message.author.bot:
        return
    if not message.content.startswith("!f"):
        return
    content = message.content.strip()
    # Format: !f<angka> <huruf>
    parts = content.split()
    cmd   = parts[0]  # misal !f1
    if len(cmd) < 3:
        return
    pos_str = cmd[2:]  # ambil angka setelah !f
    if not pos_str.isdigit():
        return
    position = int(pos_str)
    if len(parts) < 2:
        await message.channel.send(f"❌ {message.author.mention} Format: `!f{position} [huruf]`")
        return
    letter = parts[1]
    if len(letter) != 1 or not letter.isalpha():
        await message.channel.send(f"❌ {message.author.mention} Huruf harus 1 karakter alfabet!")
        return

    user_id  = str(message.author.id)
    user_name = str(message.author)
    guild_id = str(message.guild.id)

    if not is_quiz_member(guild_id, user_id):
        await message.channel.send(f"❌ {message.author.mention} kamu belum join quiz! Ketik `!qjoin` dulu.")
        return

    doc_id, soal = quiz_sys.get_active_soal(guild_id)
    if not soal:
        await message.channel.send(f"❌ {message.author.mention} tidak ada soal aktif saat ini!")
        return

    result = quiz_sys.try_fill(doc_id, soal, position, letter, user_id, user_name)

    if result.get("out_of_range"):
        answer = soal.get("answer", "")
        await message.channel.send(
            f"❌ {message.author.mention} posisi **{position}** tidak valid! "
            f"Jawaban punya **{len(answer)}** karakter."
        )
        return

    if result["already"]:
        await message.channel.send(
            f"❌ {message.author.mention} posisi **{position}** sudah ditebak orang lain!"
        )
        return

    if not result["correct"]:
        await message.channel.send(
            f"❌ {message.author.mention} huruf **{letter.upper()}** di posisi **{position}** salah!"
        )
        return

    # Benar! Beri reward
    reward      = result["reward"]
    new_balance = coin_sys.add_coins(user_id, reward)

    # Refresh soal dari Firestore
    fresh = quiz_sys.get_db().collection("quiz_soal").document(doc_id).get().to_dict()

    guild_id_str = str(message.guild.id)
    channel_id, message_id = quiz_sys.get_soal_message(guild_id_str)

    if result["completed"]:
        # Soal selesai — kirim pesan baru & hapus embed soal lama
        embed = discord.Embed(title="🎉 Soal Selesai!", color=0x00B894)
        embed.description = f"Semua huruf berhasil ditebak!\n\n**Jawaban:** `{soal['answer']}`"
        embed.add_field(name="💰 Reward", value=f"+{reward} koin → total {new_balance} koin", inline=False)
        solvers = fresh.get("solvers", {})
        if solvers:
            lines = [f"<@{uid}> — {info.get('earned',0)} koin ({len(info.get('indices',[]))} huruf)"
                     for uid, info in solvers.items()]
            embed.add_field(name="🏆 Kontributor", value="\n".join(lines), inline=False)
        next_id, next_soal = quiz_sys.activate_next_soal(guild_id_str)
        if next_soal:
            embed.add_field(name="➡️ Soal Berikutnya", value="Soal baru sudah aktif! Ketik `!soal` untuk lihat.", inline=False)
        # Hapus embed soal lama
        if channel_id and message_id:
            try:
                ch = bot.get_channel(int(channel_id))
                if ch:
                    old_msg = await ch.fetch_message(int(message_id))
                    await old_msg.delete()
            except:
                pass
        await message.channel.send(f"{message.author.mention}", embed=embed)
    else:
        # Edit embed soal yang ada
        embed = build_soal_embed(fresh)
        embed.title = f"❓ Soal Quiz (+{reward} koin untuk {message.author.display_name})"
        embed.color = 0x00B894
        edited = False
        if channel_id and message_id:
            try:
                ch = bot.get_channel(int(channel_id))
                if ch:
                    old_msg = await ch.fetch_message(int(message_id))
                    await old_msg.edit(embed=embed)
                    edited = True
                    await message.add_reaction("✅")
            except:
                pass
        if not edited:
            msg = await message.channel.send(embed=embed)
            quiz_sys.save_soal_message(guild_id_str, message.channel.id, msg.id)

# ═══════════════════════════════════════════
#  COMMAND: !kirimsoal (harus via DM)
# ═══════════════════════════════════════════
@bot.command(name="kirimsoal")
async def kirim_soal(ctx, *, args: str = None):
    # Harus via DM
    if ctx.guild is not None:
        await ctx.send(
            f"❌ {ctx.author.mention} command ini hanya bisa dipakai via **DM bot**!\n"
            f"Klik nama bot → **Message** → ketik `!kirimsoal` di sana."
        )
        return

    if not args:
        await ctx.send(
            "📝 **Format submit soal:**\n"
            "```\n!kirimsoal\n"
            "Q : [pertanyaan]\n"
            "A : [jawaban]\n"
            "MS : [jumlah huruf tampil awal, min 1]\n```\n"
            f"💰 Biaya: **{quiz_sys.COST_SUBMIT} koin**\n\n"
            "**Contoh:**\n"
            "```\n!kirimsoal\nQ : Apa ibukota Indonesia?\nA : Jakarta\nMS : 1\n```"
        )
        return

    # Parse Q, A, MS (opsional), C (opsional)
    lines = [l.strip() for l in args.strip().splitlines()]
    q_line  = next((l for l in lines if l.upper().startswith("Q")), None)
    a_line  = next((l for l in lines if l.upper().startswith("A")), None)
    ms_line = next((l for l in lines if l.upper().startswith("MS")), None)
    c_line  = next((l for l in lines if l.upper().startswith("C")), None)

    if not q_line or not a_line:
        await ctx.send("❌ Format salah! Harus ada baris `Q :` dan `A :`")
        return

    question = q_line.split(":", 1)[-1].strip()
    answer   = a_line.split(":", 1)[-1].strip()
    category = c_line.split(":", 1)[-1].strip() if c_line else "Umum"
    max_show = 0
    if ms_line:
        try:
            max_show = max(0, int(ms_line.split(":", 1)[-1].strip()))
        except:
            max_show = 0

    if not question or not answer:
        await ctx.send("❌ Pertanyaan dan jawaban tidak boleh kosong!")
        return

    # Cek koin user — tapi DM tidak punya guild_id
    # Kita simpan guild_id dari server terakhir yang dipakai (simpan di Firestore)
    user_id   = str(ctx.author.id)
    user_data = coin_sys.get_user_coins(user_id)
    last_guild = user_data.get("lastGuild")

    if not last_guild:
        await ctx.send(
            "❌ Kamu belum pernah pakai bot di server manapun!\n"
            "Ketik `!qjoin` di server dulu, lalu coba lagi."
        )
        return

    ok, new_bal = coin_sys.deduct_coins(user_id, quiz_sys.COST_SUBMIT)
    if not ok:
        await ctx.send(
            f"❌ Koin tidak cukup! Kamu punya **{user_data.get('coins',0)}** koin, "
            f"butuh **{quiz_sys.COST_SUBMIT}** koin.\n"
            f"Ketik `!claim` di server untuk klaim koin harian!"
        )
        return

    doc_id = quiz_sys.submit_soal(
        guild_id      = last_guild,
        question      = question,
        answer        = answer,
        max_show      = max_show,
        category      = category,
        submitter_name= str(ctx.author),
        submitter_id  = user_id,
    )

    embed = discord.Embed(title="✅ Soal Berhasil Dikirim!", color=0x00B894)
    embed.add_field(name="❓ Pertanyaan", value=question, inline=False)
    embed.add_field(name="✏️ Jawaban", value=answer, inline=True)
    embed.add_field(name="📂 Kategori", value=category, inline=True)
    embed.add_field(name="👁️ Max Show", value=str(max_show) if max_show > 0 else "0 (semua tersembunyi)", inline=True)
    embed.add_field(name="💰 Saldo", value=f"{new_bal} koin", inline=True)
    embed.set_footer(text="Soal masuk ke pool dan akan tampil giliran berikutnya!")
    await ctx.send(embed=embed)

# ═══════════════════════════════════════════
#  COMMAND: !j [jawaban]
# ═══════════════════════════════════════════
@bot.command(name="j")
async def jawab_penuh(ctx, *, answer_input: str = None):
    if not answer_input:
        await ctx.send("❌ Format: `!j [jawaban]`\nContoh: `!j Jakarta`")
        return

    user_id   = str(ctx.author.id)
    user_name = str(ctx.author)
    guild_id  = str(ctx.guild.id)

    if not is_quiz_member(guild_id, user_id):
        await ctx.send(f"❌ {ctx.author.mention} kamu belum join quiz! Ketik `!qjoin` dulu.")
        return

    doc_id, soal = quiz_sys.get_active_soal(guild_id)
    if not soal:
        await ctx.send(f"❌ {ctx.author.mention} tidak ada soal aktif saat ini!")
        return

    result = quiz_sys.try_answer(doc_id, soal, answer_input, user_id, user_name)

    if not result["correct"]:
        await ctx.send(f"❌ {ctx.author.mention} jawaban **{answer_input}** salah! Coba lagi.")
        return

    # Benar!
    reward      = result["reward"]
    new_balance = coin_sys.add_coins(user_id, reward)

    embed = discord.Embed(
        title="🎉 Jawaban Benar! Soal Selesai!",
        color=0x00B894
    )
    embed.description = f"**Jawaban:** `{soal['answer']}`"
    embed.add_field(name="🏆 Ditebak oleh", value=ctx.author.mention, inline=True)
    embed.add_field(name="💰 Reward", value=f"+{reward} koin → total {new_balance} koin", inline=True)

    # Tampilkan semua kontributor
    fresh = quiz_sys.get_db().collection("quiz_soal").document(doc_id).get().to_dict()
    solvers = fresh.get("solvers", {})
    if len(solvers) > 1:
        lines = []
        for uid, info in solvers.items():
            lines.append(f"<@{uid}> — {info.get('earned', 0)} koin")
        embed.add_field(name="👥 Semua Kontributor", value="\n".join(lines), inline=False)

    # Aktifkan soal berikutnya
    next_id, next_soal = quiz_sys.activate_next_soal(guild_id)
    if next_soal:
        embed.add_field(name="➡️ Soal Berikutnya", value="Soal baru sudah aktif! Ketik `!soal` untuk lihat.", inline=False)
    else:
        embed.add_field(name="📭 Pool Kosong", value="Belum ada soal berikutnya. Submit soal dengan `!kirimsoal` via DM bot!", inline=False)

    await ctx.send(embed=embed)


@bot.listen("on_command")
async def track_guild(ctx):
    if ctx.guild:
        user_id = str(ctx.author.id)
        from firebase_admin import firestore as fs
        quiz_sys.get_db().collection("users").document(user_id).set(
            {"lastGuild": str(ctx.guild.id)}, merge=True
        )

# ═══════════════════════════════════════════
#  HELPER: Build embed soal tebak gambar (reusable)
# ═══════════════════════════════════════════
def build_tg_embed(soal: dict) -> discord.Embed:
    embed = discord.Embed(title="🖼️ Tebak Gambar", color=0xA29BFE)
    embed.description = tg_sys.build_tg_display(soal)

    image_url = soal.get("imageUrl", "")
    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text="!jg [jawaban] — tebak jawaban • !tg — lihat soal lagi")
    return embed


# ═══════════════════════════════════════════
#  COMMAND: !tgjoin
#  User harus join dulu sebelum bisa ikut tebak gambar
# ═══════════════════════════════════════════
@bot.command(name="tgjoin")
async def tg_join(ctx):
    user_id  = str(ctx.author.id)
    guild_id = str(ctx.guild.id)

    tg_sys.join_tg(guild_id, user_id)

    embed = discord.Embed(
        title="🖼️ Bergabung ke Tebak Gambar!",
        description=f"{ctx.author.mention} siap bermain Tebak Gambar!",
        color=0xA29BFE
    )
    embed.add_field(
        name="📋 Command",
        value=(
            "`!tg` — Tampilkan soal aktif\n"
            "`!jg [jawaban]` — Jawab soal\n"
        ),
        inline=False
    )
    embed.set_footer(text="Belum verifikasi? DM bot dengan !v dulu!")
    await ctx.send(embed=embed)


# ═══════════════════════════════════════════
#  COMMAND: !v  (hanya via DM)
#  Generate kode verifikasi 32 karakter untuk dihubungkan ke app
# ═══════════════════════════════════════════
@bot.command(name="v")
async def verify_cmd(ctx):
    # Wajib via DM
    if ctx.guild is not None:
        await ctx.send(
            f"❌ {ctx.author.mention} command `!v` hanya bisa dipakai via **DM bot**!\n"
            f"Klik nama bot → **Message** → ketik `!v` di sana."
        )
        return

    user_id   = str(ctx.author.id)
    user_name = str(ctx.author)

    # Reset isVerified supaya user yang uninstall & install ulang app
    # bisa verifikasi ulang dengan bersih.
    # generate_verify_code() sudah pakai document(discord_id).set()
    # sehingga otomatis menimpa kode lama — 1 user = 1 dokumen aktif.
    tg_sys.get_db().collection("users").document(user_id).set(
        {"isVerified": False}, merge=True
    )

    code = tg_sys.generate_verify_code(user_id, user_name)

    embed = discord.Embed(
        title="🔐 Kode Verifikasi Akun Discord",
        description=(
            "Salin kode di bawah ini dan masukkan ke aplikasi untuk menghubungkan "
            "akun Discord kamu.\n\n"
            "**Kode ini berlaku selama 24 jam dan hanya bisa dipakai 1 kali.**"
        ),
        color=0x00CEC9
    )
    embed.add_field(
        name="🔑 Kode Verifikasimu",
        value=f"```\n{code}\n```",
        inline=False
    )
    embed.add_field(
        name="📱 Cara Pakai",
        value=(
            "1. Buka aplikasi\n"
            "2. Masuk ke menu **Verifikasi Discord**\n"
            "3. Paste kode di atas\n"
            "4. Tekan **Verifikasi**"
        ),
        inline=False
    )
    embed.set_footer(text="Jangan bagikan kode ini ke siapapun!")
    await ctx.send(embed=embed)


# ═══════════════════════════════════════════
#  COMMAND: !tg
#  Tampilkan soal tebak gambar aktif di server ini
# ═══════════════════════════════════════════
@bot.command(name="tg")
async def tampil_soal_tg(ctx):
    user_id  = str(ctx.author.id)
    guild_id = str(ctx.guild.id)

    if not tg_sys.is_tg_member(guild_id, user_id):
        await ctx.send(
            f"❌ {ctx.author.mention} kamu belum join! Ketik `!tgjoin` dulu."
        )
        return

    doc_id, soal = tg_sys.get_active_soal_tg(guild_id)
    if not soal:
        # Coba aktifkan soal berikutnya dari pool approved
        doc_id, soal = tg_sys.activate_next_soal_tg(guild_id)

    if not soal:
        await ctx.send(
            f"📭 {ctx.author.mention} belum ada soal tebak gambar aktif di server ini!\n"
            f"Submit soal baru lewat aplikasi."
        )
        return

    embed = build_tg_embed(soal)
    msg   = await ctx.send(embed=embed)
    tg_sys.save_tg_message(guild_id, ctx.channel.id, msg.id)


# ═══════════════════════════════════════════
#  COMMAND: !jg [jawaban]
#  Jawab soal tebak gambar
#  Kalau salah → bot reply dengan jawaban salah dalam code block
#  supaya user bisa copy & revisi cepat
# ═══════════════════════════════════════════
@bot.command(name="jg")
async def jawab_tg(ctx, *, answer_input: str = None):
    if not answer_input:
        await ctx.send(
            f"❌ {ctx.author.mention} Format: `!jg [jawaban]`\nContoh: `!jg Nasi Goreng`"
        )
        return

    user_id   = str(ctx.author.id)
    user_name = str(ctx.author)
    guild_id  = str(ctx.guild.id)

    if not tg_sys.is_tg_member(guild_id, user_id):
        await ctx.send(
            f"❌ {ctx.author.mention} kamu belum join! Ketik `!tgjoin` dulu."
        )
        return

    doc_id, soal = tg_sys.get_active_soal_tg(guild_id)
    if not soal:
        await ctx.send(
            f"❌ {ctx.author.mention} tidak ada soal aktif saat ini!"
        )
        return

    result = tg_sys.try_answer_tg(doc_id, soal, answer_input, user_id, user_name)

    if not result["correct"]:
        # ── Jawaban salah: tampilkan jawaban salah dalam code block ──
        wrong_embed = discord.Embed(color=0xD63031)
        wrong_embed.description = (
            f"❌ {ctx.author.mention} jawaban salah! Cek ejaan dan coba lagi.\n\n"
            f"Salin jawaban kamu untuk direvisi:"
        )
        wrong_embed.add_field(
            name="✏️ Jawaban yang kamu ketik",
            value=f"```\n!jg {answer_input}\n```",
            inline=False
        )
        wrong_embed.set_footer(text="Salin teks di atas, lalu perbaiki ejaannya!")
        await ctx.reply(embed=wrong_embed, mention_author=False)
        return

    # ── Jawaban benar! ──
    reward      = result["reward"]
    new_balance = coin_sys.add_coins(user_id, reward)

    embed = discord.Embed(
        title="🎉 Jawaban Benar! Soal Selesai!",
        color=0x00B894
    )
    embed.description = f"**Jawaban:** `{soal['answer']}`"
    embed.add_field(name="🏆 Ditebak oleh", value=ctx.author.mention, inline=True)
    embed.add_field(
        name="💰 Reward",
        value=f"+{reward} koin → total **{new_balance}** koin",
        inline=True
    )

    # Tampilkan gambar soal sebagai konfirmasi
    image_url = soal.get("imageUrl", "")
    if image_url:
        embed.set_image(url=image_url)

    # Aktifkan soal berikutnya
    next_id, next_soal = tg_sys.activate_next_soal_tg(guild_id)
    if next_soal:
        embed.add_field(
            name="➡️ Soal Berikutnya",
            value="Soal baru sudah aktif! Ketik `!tg` untuk lihat.",
            inline=False
        )
    else:
        embed.add_field(
            name="📭 Pool Kosong",
            value="Belum ada soal berikutnya. Submit soal baru lewat aplikasi!",
            inline=False
        )

    # Hapus embed soal lama
    channel_id, message_id = tg_sys.get_tg_message(guild_id)
    if channel_id and message_id:
        try:
            ch = bot.get_channel(int(channel_id))
            if ch:
                old_msg = await ch.fetch_message(int(message_id))
                await old_msg.delete()
        except Exception:
            pass

    await ctx.send(embed=embed)


# ═══════════════════════════════════════════
#  JALANKAN BOT
# ═══════════════════════════════════════════
token = os.environ.get("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN tidak ditemukan di environment variables!")

bot.run(token)
