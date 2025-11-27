from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3
import time
from typing import Optional, List, Dict, Any

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "app.sqlite3"

app = FastAPI(title="De Che Dau Den WebApp")

# ============ DB ============

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
            amount_xu REAL NOT NULL,
            phone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL
        )
        """
    )

    # Bảng người chơi: dầu, xu, level, cooldown
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            tg_id TEXT PRIMARY KEY,
            username TEXT,
            oil REAL NOT NULL DEFAULT 0,
            xu   REAL NOT NULL DEFAULT 0,
            rig_level INTEGER NOT NULL DEFAULT 1,
            last_mine_at_ms INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


init_db()

# ============ GAME CONFIG ============

OIL_PER_XU = 1000          # 10 xu = 1000 vnd -> 1 xu = 100vnd -> tuỳ logic sau này
MINE_COOLDOWN_MS = 5 * 60 * 1000
RIG_MAX_LEVEL = 10

LEVEL_CONFIG = {
    1:  {"upgrade_cost_from_prev":      0, "payout_oil":  17.5},
    2:  {"upgrade_cost_from_prev":   5000, "payout_oil":  35.0},
    3:  {"upgrade_cost_from_prev":  12000, "payout_oil":  52.5},
    4:  {"upgrade_cost_from_prev":  25000, "payout_oil":  70.0},
    5:  {"upgrade_cost_from_prev":  50000, "payout_oil":  87.5},
    6:  {"upgrade_cost_from_prev": 100000, "payout_oil": 105.0},
    7:  {"upgrade_cost_from_prev": 200000, "payout_oil": 122.5},
    8:  {"upgrade_cost_from_prev": 400000, "payout_oil": 140.0},
    9:  {"upgrade_cost_from_prev": 800000, "payout_oil": 157.5},
    10: {"upgrade_cost_from_prev":1500000, "payout_oil": 175.0},
}


def now_ms() -> int:
    return int(time.time() * 1000)


def get_or_create_player(tg_id: str, username: Optional[str]) -> sqlite3.Row:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    if row:
        # cập nhật username nếu đổi
        if username and row["username"] != username:
            cur.execute(
                "UPDATE players SET username = ? WHERE tg_id = ?",
                (username, tg_id),
            )
            conn.commit()
            cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
            row = cur.fetchone()
        conn.close()
        return row

    # tạo mới
    created = int(time.time())
    cur.execute(
        """
        INSERT INTO players (tg_id, username, oil, xu, rig_level, last_mine_at_ms, created_at)
        VALUES (?, ?, 0, 0, 1, 0, ?)
        """,
        (tg_id, username, created),
    )
    conn.commit()
    cur.execute("SELECT * FROM players WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    return row


def row_to_player_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "tg_id": row["tg_id"],
        "username": row["username"],
        "oil": row["oil"],
        "xu": row["xu"],
        "rig_level": row["rig_level"],
        "last_mine_at_ms": row["last_mine_at_ms"],
    }


# ============ MODELS ============

class WithdrawRequestIn(BaseModel):
    tg_id: str
    username: Optional[str] = None
    amount_xu: float = Field(..., ge=1)
    phone: str


class WithdrawRequestOut(BaseModel):
    id: int
    amount_xu: float
    phone: str
    status: str
    created_at: int


class StateOut(BaseModel):
    tg_id: str
    username: Optional[str]
    oil: float
    xu: float
    rig_level: int
    last_mine_at_ms: int
    payout_oil: float


class MineIn(BaseModel):
    tg_id: str
    username: Optional[str] = None


class UpgradeIn(BaseModel):
    tg_id: str
    username: Optional[str] = None


# ============ API GAME ============

@app.get("/api/state", response_model=StateOut)
def api_state(tg_id: str = Query(...), username: Optional[str] = None):
    """
    Lấy trạng thái người chơi. Nếu chưa có thì tạo mới.
    """
    row = get_or_create_player(tg_id, username)
    level = row["rig_level"]
    cfg = LEVEL_CONFIG.get(level, LEVEL_CONFIG[1])
    return StateOut(
        **row_to_player_dict(row),
        payout_oil=cfg["payout_oil"],
    )


@app.post("/api/mine", response_model=StateOut)
def api_mine(body: MineIn):
    """
    Thực hiện đào dầu: check cooldown + cộng Dầu theo level.
    """
    row = get_or_create_player(body.tg_id, body.username)
    level = row["rig_level"]
    cfg = LEVEL_CONFIG.get(level, LEVEL_CONFIG[1])

    now = now_ms()
    last = row["last_mine_at_ms"]
    diff = now - last
    if diff < MINE_COOLDOWN_MS:
        remain = MINE_COOLDOWN_MS - diff
        raise HTTPException(
            status_code=400,
            detail=f"Đang cooldown, còn {int(remain/1000)}s nữa.",
        )

    new_oil = row["oil"] + cfg["payout_oil"]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE players
        SET oil = ?, last_mine_at_ms = ?
        WHERE tg_id = ?
        """,
        (new_oil, now, body.tg_id),
    )
    conn.commit()
    cur.execute("SELECT * FROM players WHERE tg_id = ?", (body.tg_id,))
    row2 = cur.fetchone()
    conn.close()

    level2 = row2["rig_level"]
    cfg2 = LEVEL_CONFIG.get(level2, LEVEL_CONFIG[1])
    return StateOut(
        **row_to_player_dict(row2),
        payout_oil=cfg2["payout_oil"],
    )


@app.post("/api/upgrade", response_model=StateOut)
def api_upgrade(body: UpgradeIn):
    """
    Nâng cấp giàn khoan: trừ Dầu theo bảng LEVEL_CONFIG.
    """
    row = get_or_create_player(body.tg_id, body.username)
    cur_level = row["rig_level"]

    if cur_level >= RIG_MAX_LEVEL:
        raise HTTPException(status_code=400, detail="Đã max level.")

    next_level = cur_level + 1
    cfg_next = LEVEL_CONFIG.get(next_level)
    if not cfg_next:
        raise HTTPException(status_code=400, detail="Không tìm thấy config level.")

    cost = cfg_next["upgrade_cost_from_prev"]
    if row["oil"] < cost:
        raise HTTPException(
            status_code=400,
            detail=f"Không đủ Dầu. Cần {cost} Dầu để lên Lv.{next_level}.",
        )

    new_oil = row["oil"] - cost

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE players
        SET oil = ?, rig_level = ?
        WHERE tg_id = ?
        """,
        (new_oil, next_level, body.tg_id),
    )
    conn.commit()
    cur.execute("SELECT * FROM players WHERE tg_id = ?", (body.tg_id,))
    row2 = cur.fetchone()
    conn.close()

    level2 = row2["rig_level"]
    cfg2 = LEVEL_CONFIG.get(level2, LEVEL_CONFIG[1])
    return StateOut(
        **row_to_player_dict(row2),
        payout_oil=cfg2["payout_oil"],
    )


# ============ API RÚT TIỀN ============

@app.post("/api/withdraw", response_model=WithdrawRequestOut)
def create_withdraw(req: WithdrawRequestIn):
    # min 200 Xu
    if req.amount_xu < 200:
        raise HTTPException(status_code=400, detail="Min rút là 200 Xu")

    if not req.phone.startswith("84") or len(req.phone) < 9:
        raise HTTPException(
            status_code=400,
            detail="Số điện thoại phải dạng 84xxxxxxxxx",
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
def withdraw_history(tg_id: str = Query(...)):
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


# ============ STATIC WEBAPP ============

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")