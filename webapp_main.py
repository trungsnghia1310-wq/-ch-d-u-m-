from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3
import time
from typing import Optional, List

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "withdraws.sqlite3"

app = FastAPI(title="De Che Dau Den WebApp")

# ------------------ DB ------------------


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
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
    conn.commit()
    conn.close()


init_db()

# ------------------ MODELS ------------------


class WithdrawRequestIn(BaseModel):
    tg_id: str = Field(..., description="Telegram user id")
    username: Optional[str] = None
    amount_xu: int = Field(..., ge=1)
    phone: str


class WithdrawRequestOut(BaseModel):
    id: int
    amount_xu: int
    phone: str
    status: str
    created_at: int


# ------------------ API ------------------


@app.post("/api/withdraw", response_model=WithdrawRequestOut)
def create_withdraw(req: WithdrawRequestIn):
    # validate basic rules: min 200 xu, phone 84...
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
        "SELECT id, amount_xu, phone, status, created_at FROM withdraw_requests WHERE id = ?",
        (new_id,),
    )
    row = cur.fetchone()
    conn.close()
    return WithdrawRequestOut(**dict(row))


@app.get("/api/withdraw-history", response_model=List[WithdrawRequestOut])
def withdraw_history(tg_id: str = Query(..., description="Telegram user id")):
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


# ------------------ STATIC WEBAPP ------------------


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")