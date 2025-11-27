from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3
import time
from typing import Optional, List

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "game.sqlite3"

app = FastAPI(title="De Che Dau Den WebApp")

# -------------------- DATABASE --------------------


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Bảng rút tiền
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id TEXT NOT NULL,
            username TEXT,
            amount_xu INTEGER NOT NULL,
            phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL
        )
        """
    )

    # Bảng trạng thái game
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            tg_id TEXT PRIMARY KEY,
            username TEXT,
            xu INTEGER NOT NULL DEFAULT 0,
            oil REAL NOT NULL DEFAULT 0,
            pump_level INTEGER NOT NULL DEFAULT 1,
            pump_speed REAL NOT NULL DEFAULT 1,
            last_updated INTEGER NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


init_db()

# -------------------- MODELS --------------------


class WithdrawRequestIn(BaseModel):
    tg_id: str
    username: Optional[str] = None
    amount_xu: int = Field(..., ge=1)
    phone: str


class WithdrawRequestOut(BaseModel):
    id: int
    amount_xu: int
    phone: str
    status: str
    created_at: int


class PlayerStateIn(BaseModel):
    tg_id: str
    username: Optional[str] = None
    xu: int = Field(..., ge=0)
    oil: float = Field(..., ge=0)
    pump_level: int = Field(..., ge=1)
    pump_speed: float = Field(..., ge=0)


class PlayerStateOut(BaseModel):
    tg_id: str
    username: Optional[str] = None
    xu: int
    oil: float
    pump_level: int
    pump_speed: float
    last_updated: int


# ---------------- PHASE 1: WITHDRAW API ----------------


@app.post("/api/withdraw", response_model=WithdrawRequestOut)
def create_withdraw(req: WithdrawRequestIn):
    if req.amount_xu < 200:
        raise HTTPException(status_code=400, detail="Min rút là 200 Xu")

    if not req.phone.startswith("84") or len(req.phone) < 9:
        raise HTTPException(
            status_code=400, detail="Số điện thoại phải dạng 84xxxxxxxxx"
        )

    now = int(time.time())
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO withdraw_requests (tg_id, username, amount_xu, phone, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (req.tg_id, req.username, req.amount_xu, req.phone, now),
    )
    conn.commit()
    new_id = cur.lastrowid
    cur.execute(
        "SELECT id, amount_xu, phone, status, created_at "
        "FROM withdraw_requests WHERE id = ?",
        (new_id,),
    )
    row = cur.fetchone()
    conn.close()
    return WithdrawRequestOut(**dict(row))


@app.get("/api/withdraw-history", response_model=List[WithdrawRequestOut])
def withdraw_history(
    tg_id: str = Query(..., description="Telegram user id"),
):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, amount_xu, phone, status, created_at
        FROM withdraw_requests
        WHERE tg_id = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (tg_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [WithdrawRequestOut(**dict(r)) for r in rows]


# ---------------- PHASE 2: GAME STATE API ----------------


@app.get("/api/player/state", response_model=PlayerStateOut)
def get_state(tg_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()

    if row is None:
        now = int(time.time())
        cur.execute(
            """
            INSERT INTO players (tg_id, username, xu, oil, pump_level, pump_speed, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tg_id, None, 0, 0.0, 1, 1.0, now),
        )
        conn.commit()
        cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
        row = cur.fetchone()

    conn.close()
    return PlayerStateOut(**dict(row))


@app.post("/api/player/state", response_model=PlayerStateOut)
def save_state(state: PlayerStateIn):
    # anti-cheat nhẹ
    if state.xu > 50_000_000 or state.oil > 50_000_000:
        raise HTTPException(status_code=400, detail="Giá trị quá lớn, nghi ngờ cheat")

    now = int(time.time())
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT tg_id FROM players WHERE tg_id = ?", (state.tg_id,))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute(
            """
            UPDATE players
            SET username = ?, xu = ?, oil = ?, pump_level = ?, pump_speed = ?, last_updated = ?
            WHERE tg_id = ?
            """,
            (
                state.username,
                state.xu,
                state.oil,
                state.pump_level,
                state.pump_speed,
                now,
                state.tg_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO players (tg_id, username, xu, oil, pump_level, pump_speed, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.tg_id,
                state.username,
                state.xu,
                state.oil,
                state.pump_level,
                state.pump_speed,
                now,
            ),
        )

    conn.commit()
    cur.execute("SELECT * FROM players WHERE tg_id = ?", (state.tg_id,))
    row = cur.fetchone()
    conn.close()
    return PlayerStateOut(**dict(row))


# ---------------- STATIC FILES ----------------


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")