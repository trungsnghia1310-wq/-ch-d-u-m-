import os
import asyncio
import time
import random
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========= WEBAPP BACKEND =========
WEBAPP_URL = "https://chdum.fly.dev"

WITHDRAW_URL = f"{WEBAPP_URL}/api/withdraw"
WITHDRAW_HISTORY_URL = f"{WEBAPP_URL}/api/withdraw-history"
PLAYER_STATE_URL = f"{WEBAPP_URL}/api/player/state"
# ==================================

# Config from environment
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN env BOT_TOKEN chưa được set trong Fly.io")

DB = os.getenv("DB_PATH", "oil_mining.db")
COOLDOWN_HOURS = int(os.getenv("COOLDOWN_HOURS", "6"))

# ---------------------- DATABASE INIT ----------------------
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE,
        username TEXT,
        oil INTEGER DEFAULT 0,
        black_oil INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 0,
        last_mine INTEGER DEFAULT 0,
        ad_pending INTEGER DEFAULT 0,
        ref_by INTEGER DEFAULT NULL,
        level INTEGER DEFAULT 1,
        created_at INTEGER
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ref_id INTEGER,
        created_at INTEGER
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_checkin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        last_day INTEGER,
        streak INTEGER DEFAULT 0
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        reward INTEGER,
        type TEXT,
        created_at INTEGER
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS task_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_id INTEGER,
        completed INTEGER DEFAULT 0,
        completed_at INTEGER
    )""")
    con.commit()
    con.close()

# Utility DB wrappers
def get_user(tg_id):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))
    row = cur.fetchone()
    con.close()
    return row

def create_user(tg_id, username, ref):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    now = int(time.time())
    cur.execute(
        "INSERT OR IGNORE INTO users (tg_id, username, ref_by, created_at) "
        "VALUES (?,?,?,?)",
        (tg_id, username, ref, now),
    )
    con.commit()
    con.close()

def update_user_field(tg_id, field, value):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(f"UPDATE users SET {field}=? WHERE tg_id=?", (value, tg_id))
    con.commit()
    con.close()

# ---------------------- BOT SETUP ----------------------
bot = Bot(TOKEN)
dp = Dispatcher()

# Helper keyboards
def main_inline_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⛽ Khai thác dầu", callback_data="mine")
    kb.button(text="🎞 Xem quảng cáo", callback_data="watch_ad")
    kb.button(text="📅 Điểm danh", callback_data="checkin")
    kb.button(text="🎁 Nhiệm vụ", callback_data="tasks")
    kb.button(text="👥 Giới thiệu bạn bè", callback_data="referral")
    kb.button(text="💱 Quy đổi", callback_data="convert")
    return kb.as_markup()

# ---------------------- START ----------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.text.split()
    ref = None
    if len(args) > 1 and args[1].isdigit():
        ref = int(args[1])

    create_user(message.from_user.id, message.from_user.username or "", ref)

    await message.answer(
        "🛢️ Bạn là nhà đầu tư vừa mở mỏ dầu mới!\n"
        "Nâng cấp dàn khoan, khai thác dầu đen, đổi xu để rút tiền.",
        reply_markup=main_inline_kb(),
    )

# ---------------------- WATCH AD ----------------------
@dp.callback_query(lambda c: c.data == "watch_ad")
async def watch_ad(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    update_user_field(tg_id, "ad_pending", 1)
    kb = InlineKeyboardBuilder()
    kb.button(text="Tôi đã xem quảng cáo", callback_data="ad_done")
    await cq.message.answer(
        "🎞 Hãy xem quảng cáo để mở khóa lượt khai thác.",
        reply_markup=kb.as_markup(),
    )
    await cq.answer()

@dp.callback_query(lambda c: c.data == "ad_done")
async def ad_done(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    update_user_field(tg_id, "ad_pending", 0)
    await cq.message.answer("✔️ Quảng cáo xác nhận! Bạn có thể khai thác dầu.")
    await cq.answer()

# ---------------------- MINE ----------------------
@dp.callback_query(lambda c: c.data == "mine")
async def mine(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    user = get_user(tg_id)
    if not user:
        await cq.answer("Chưa có tài khoản.")
        return

    # user tuple: (id, tg_id, username, oil, black_oil, coins,
    #              last_mine, ad_pending, ref_by, level, created_at)
    _, _, _, oil, black_oil, coins, last_mine, ad_pending, ref_by, level, created_at = user
    now = int(time.time())

    if ad_pending:
        await cq.message.answer("⚠️ Bạn cần xem quảng cáo trước.")
        await cq.answer()
        return

    if last_mine and now - last_mine < COOLDOWN_HOURS * 3600:
        remain = (COOLDOWN_HOURS * 3600) - (now - last_mine)
        h = remain // 3600
        m = (remain % 3600) // 60
        await cq.message.answer(f"⏳ Còn {h} giờ {m} phút mới khai thác lại được.")
        await cq.answer()
        return

    gained = random.randint(30, 90)
    new_oil = oil + gained

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET oil = ?, last_mine = ? WHERE tg_id = ?",
        (new_oil, now, tg_id),
    )
    con.commit()
    con.close()

    await cq.message.answer(f"🛢️ Bạn khai thác được {gained} lít dầu! Tổng: {new_oil}")
    await cq.answer()

# ---------------------- DAILY CHECKIN ----------------------
@dp.callback_query(lambda c: c.data == "checkin")
async def checkin(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "SELECT id, last_day, streak FROM daily_checkin "
        "WHERE user_id=(SELECT id FROM users WHERE tg_id=?)",
        (tg_id,),
    )
    row = cur.fetchone()
    today = int(time.time()) // 86400

    if not row:
        cur.execute(
            """
            INSERT INTO daily_checkin (user_id, last_day, streak)
            VALUES ((SELECT id FROM users WHERE tg_id=?), ?, ?)
            """,
            (tg_id, today, 1),
        )
        reward = 20
    else:
        _, last_day, streak = row
        if last_day == today:
            await cq.message.answer("📅 Hôm nay bạn đã điểm danh rồi.")
            con.close()
            await cq.answer()
            return
        if last_day == today - 1:
            streak += 1
        else:
            streak = 1
        reward = 20 + streak * 5
        cur.execute(
            "UPDATE daily_checkin SET last_day=?, streak=? "
            "WHERE user_id=(SELECT id FROM users WHERE tg_id=?)",
            (today, streak, tg_id),
        )

    cur.execute(
        "UPDATE users SET black_oil = black_oil + ? WHERE tg_id=?",
        (reward, tg_id),
    )
    con.commit()
    con.close()

    await cq.message.answer(f"📅 Điểm danh thành công! Nhận {reward} dầu đen.")
    await cq.answer()

# ---------------------- TASKS ----------------------
@dp.callback_query(lambda c: c.data == "tasks")
async def show_tasks(cq: types.CallbackQuery):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id, title, url, reward FROM tasks")
    tasks = cur.fetchall()
    con.close()

    if not tasks:
        await cq.message.answer("Chưa có nhiệm vụ.")
        await cq.answer()
        return

    text = "🎁 Nhiệm vụ:\n"
    for tid, title, url, reward in tasks:
        text += f"\n➡️ <b>{title}</b> (+{reward} dầu đen)\n/link_task_{tid}"

    await cq.message.answer(text, parse_mode="HTML")
    await cq.answer()

# ---------------------- REFERRAL ----------------------
@dp.callback_query(lambda c: c.data == "referral")
async def referral(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={tg_id}"
    await cq.message.answer(f"👥 Mời bạn bè:\nGửi link sau:\n{link}")
    await cq.answer()

# ---------------------- CONVERT BLACK OIL -> COINS ----------------------
@dp.callback_query(lambda c: c.data == "convert")
async def convert(cq: types.CallbackQuery):
    tg_id = cq.from_user.id
    user = get_user(tg_id)
    if not user:
        await cq.answer()
        return

    black = user[4]
    rate = 10
    coins = black * rate

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET black_oil = 0, coins = coins + ? WHERE tg_id=?",
        (coins, tg_id),
    )
    con.commit()
    con.close()

    await cq.message.answer(f"💱 Đổi {black} dầu đen thành {coins} xu thành công!")
    await cq.answer()

# ---------------------- MAIN ----------------------
async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())