from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import sqlite3
from pathlib import Path
import time
from typing import Optional, List

BASE = Path(__file__).parent
DB = BASE / "game.sqlite3"

app = FastAPI(title="De Che Dau Den WebApp")

# -------------------- DATABASE --------------------

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()

    # bảng rút tiền (phase 1)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdraw_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id TEXT,
            username TEXT,
            amount_xu INTEGER,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            created_at INTEGER
        )
    """)

    # bảng state game (phase 2)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS players(
            tg_id TEXT PRIMARY KEY,
            username TEXT,
            xu INTEGER DEFAULT 0,
            oil REAL DEFAULT 0,
            pump_level INTEGER DEFAULT 1,
            pump_speed REAL DEFAULT 1,
            last_updated INTEGER
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------- MODELS --------------------

class WithdrawIn(BaseModel):
    tg_id: str
    username: Optional[str]
    amount_xu: int = Field(..., ge=1)
    phone: str

class WithdrawOut(BaseModel):
    id: int
    amount_xu: int
    phone: str
    status: str
    created_at: int

class PlayerStateIn(BaseModel):
    tg_id: str
    username: Optional[str]
    xu: int = Field(..., ge=0)
    oil: float = Field(..., ge=0)
    pump_level: int = Field(..., ge=1)
    pump_speed: float = Field(..., ge=0)

class PlayerStateOut(BaseModel):
    tg_id: str
    username: Optional[str]
    xu: int
    oil: float
    pump_level: int
    pump_speed: float
    last_updated: int

# --------------- PHASE 1: WITHDRAW API ----------------

@app.post("/api/withdraw", response_model=WithdrawOut)
def create_withdraw(req: WithdrawIn):
    if req.amount_xu < 200:
        raise HTTPException(400, "Min rút là 200 Xu")

    if not req.phone.startswith("84"):
        raise HTTPException(400, "Số điện thoại phải dạng 84xxxxxxxx")

    now = int(time.time())
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO withdraw_requests(tg_id, username, amount_xu, phone, created_at)
        VALUES(?,?,?,?,?)
    """, (req.tg_id, req.username, req.amount_xu, req.phone, now))

    conn.commit()
    new_id = cur.lastrowid
    cur.execute("SELECT id, amount_xu, phone, status, created_at FROM withdraw_requests WHERE id = ?", (new_id,))
    row = cur.fetchone()
    conn.close()
    return WithdrawOut(**dict(row))

@app.get("/api/withdraw-history", response_model=List[WithdrawOut])
def withdraw_history(tg_id: str):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, amount_xu, phone, status, created_at
        FROM withdraw_requests
        WHERE tg_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return [WithdrawOut(**dict(r)) for r in rows]

# --------------- PHASE 2: GAME STATE API ----------------

@app.get("/api/player/state", response_model=PlayerStateOut)
def get_state(tg_id: str):
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()

    if row is None:
        now = int(time.time())
        cur.execute("""
            INSERT INTO players(tg_id, username, xu, oil, pump_level, pump_speed, last_updated)
            VALUES(?,?,?,?,?,?,?)
        """, (tg_id, None, 0, 0, 1, 1, now))
        conn.commit()
        cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
        row = cur.fetchone()

    conn.close()
    return PlayerStateOut(**dict(row))

@app.post("/api/player/state", response_model=PlayerStateOut)
def save_state(state: PlayerStateIn):
    # anti-cheat nhẹ
    if state.xu > 50_000_000 or state.oil > 50_000_000:
        raise HTTPException(400, "Giá trị quá lớn, nghi ngờ cheat")

    conn = db()
    cur = conn.cursor()

    now = int(time.time())
    cur.execute("SELECT tg_id FROM players WHERE tg_id = ?", (state.tg_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("""
            UPDATE players
            SET username=?, xu=?, oil=?, pump_level=?, pump_speed=?, last_updated=?
            WHERE tg_id=?
        """, (state.username, state.xu, state.oil, state.pump_level, state.pump_speed, now, state.tg_id))
    else:
        cur.execute("""
            INSERT INTO players(tg_id, username, xu, oil, pump_level, pump_speed, last_updated)
            VALUES(?,?,?,?,?,?,?)
        """, (state.tg_id, state.username, state.xu, state.oil, state.pump_level, state.pump_speed, now))

    conn.commit()
    cur.execute("SELECT * FROM players WHERE tg_id = ?", (state.tg_id,))
    row = cur.fetchone()
    conn.close()
    return PlayerStateOut(**dict(row))

# --------------- STATIC FILES ----------------

app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")

@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")