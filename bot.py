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
        name="🎮 Cara Main",
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
#  JALANKAN BOT
# ═══════════════════════════════════════════
token = os.environ.get("DISCORD_TOKEN")
if not token:
    raise ValueError("DISCORD_TOKEN tidak ditemukan di environment variables!")

bot.run(token)
