# webapp_main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3
import time
from typing import Optional, List

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "withdraws.sqlite3"  # dùng luôn file cũ

app = FastAPI(title="De Che Dau Den WebApp")

# -------------------------------------------------
# DB helpers
# -------------------------------------------------


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

    # Bảng trạng thái game (đào dầu, nâng cấp)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_state (
            tg_id TEXT PRIMARY KEY,
            username TEXT,
            oil REAL NOT NULL DEFAULT 0,
            xu INTEGER NOT NULL DEFAULT 0,
            mine_level INTEGER NOT NULL DEFAULT 1,   -- level mũi khoan
            pump_level INTEGER NOT NULL DEFAULT 1,   -- level bơm / nâng cấp khác
            updated_at INTEGER NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


init_db()

# -------------------------------------------------
# MODELS
# -------------------------------------------------


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


class UserStateIn(BaseModel):
    tg_id: str = Field(..., description="Telegram user id")
    username: Optional[str] = None
    oil: float = Field(..., ge=0)
    xu: int = Field(..., ge=0)
    mine_level: int = Field(1, ge=1)
    pump_level: int = Field(1, ge=1)


class UserStateOut(UserStateIn):
    updated_at: int


# -------------------------------------------------
# API: RÚT TIỀN
# -------------------------------------------------


@app.post("/api/withdraw", response_model=WithdrawRequestOut)
def create_withdraw(req: WithdrawRequestIn):
    # validate basic rules
    if req.amount_xu < 200:
        raise HTTPException(status_code=400, detail="Min rút là 200 Xu")

    if not req.phone.startswith("84") or len(req.phone) < 9:
        raise HTTPException(
            status_code=400, detail="Số điện thoại phải dạng 84xxxxxxxxx"
        )

    now = int(time.time())
    conn = get_conn()
    cur = conn.cursor()

    # (Không trừ xu ở đây – xu sẽ do bot Telegram xử lý
    #  hoặc bạn có thể tự trừ sau nếu muốn.)

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
        """
        SELECT id, amount_xu, phone, status, created_at
        FROM withdraw_requests
        WHERE id = ?
        """,
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


# -------------------------------------------------
# API: GAME STATE (ĐÀO DẦU + NÂNG CẤP)
# -------------------------------------------------
# Ý tưởng: gameplay (tính xu, dầu, level) vẫn chạy trên client,
# nhưng mỗi lần có thay đổi, web gửi "snapshot" lên backend:
#   oil, xu, mine_level, pump_level
# Backend lưu lại để:
#   - Kiểm tra khi rút tiền
#   - Xem lịch sử / dashboard sau này


@app.get("/api/state", response_model=UserStateOut)
def get_state(tg_id: str = Query(..., description="Telegram user id")):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT tg_id, username, oil, xu, mine_level, pump_level, updated_at
        FROM user_state
        WHERE tg_id = ?
        """,
        (tg_id,),
    )
    row = cur.fetchone()
    conn.close()

    now = int(time.time())

    if row is None:
        # Nếu chưa có thì trả về default
        return UserStateOut(
            tg_id=tg_id,
            username=None,
            oil=0.0,
            xu=0,
            mine_level=1,
            pump_level=1,
            updated_at=now,
        )

    data = dict(row)
    return UserStateOut(
        tg_id=data["tg_id"],
        username=data["username"],
        oil=data["oil"],
        xu=data["xu"],
        mine_level=data["mine_level"],
        pump_level=data["pump_level"],
        updated_at=data["updated_at"],
    )


@app.post("/api/state", response_model=UserStateOut)
def upsert_state(state: UserStateIn):
    now = int(time.time())
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO user_state (tg_id, username, oil, xu, mine_level, pump_level, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username = excluded.username,
            oil = excluded.oil,
            xu = excluded.xu,
            mine_level = excluded.mine_level,
            pump_level = excluded.pump_level,
            updated_at = excluded.updated_at
        """,
        (
            state.tg_id,
            state.username,
            float(state.oil),
            int(state.xu),
            int(state.mine_level),
            int(state.pump_level),
            now,
        ),
    )

    conn.commit()
    conn.close()

    return UserStateOut(**state.dict(), updated_at=now)


# -------------------------------------------------
# STATIC WEBAPP
# -------------------------------------------------

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")