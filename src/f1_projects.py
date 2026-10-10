"""Chức năng 1: Quản lý dự án điện mặt trời (SQLite)."""
import json, sqlite3
from config import DB_PATH, RAW_DIR, SYSTEM_ID, DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id   INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    owner        TEXT NOT NULL,          -- địa chỉ ví nhận chứng chỉ
    capacity_kw  REAL NOT NULL CHECK (capacity_kw > 0),  -- công suất DC
    location     TEXT,
    latitude     REAL, longitude REAL,
    tilt         REAL, azimuth REAL,
    started_on   TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS daily_production (
    project_id   INTEGER NOT NULL REFERENCES projects(project_id),
    date         TEXT NOT NULL,
    meter_kwh REAL, inverter_kwh REAL, poa_kwh_m2 REAL, amb_temp REAL,
    PRIMARY KEY (project_id, date)
);
"""


def connect():
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def add_project(project_id, name, owner, capacity_kw, **extra):
    cols = ["project_id", "name", "owner", "capacity_kw"] + list(extra)
    vals = [project_id, name, owner, capacity_kw] + list(extra.values())
    with connect() as con:
        con.execute(f"INSERT INTO projects ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)


def get_project(project_id):
    with connect() as con:
        r = con.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return dict(r) if r else None


def list_projects():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM projects ORDER BY project_id")]


def production_summary(project_id):
    """Công suất phát điện: tổng/trung bình/lớn nhất theo ngày + hệ số công suất (capacity factor)."""
    with connect() as con:
        r = con.execute("""SELECT COUNT(*) n, MIN(date) first, MAX(date) last, SUM(meter_kwh) total_kwh,
                           AVG(meter_kwh) avg_kwh, MAX(meter_kwh) max_kwh FROM daily_production
                           WHERE project_id=?""", (project_id,)).fetchone()
        p = get_project(project_id)
        s = dict(r)
        if s["n"]:
            s["capacity_factor_pct"] = round(100 * s["avg_kwh"] / (p["capacity_kw"] * 24), 2)
        return s


def load_production(project_id, daily_df):
    rows = [(project_id, d.strftime("%Y-%m-%d"), r.meter_kwh, r.inverter_kwh, r.poa_kwh_m2, r.amb_temp)
            for d, r in daily_df.iterrows()]
    with connect() as con:
        con.executemany("INSERT OR REPLACE INTO daily_production VALUES (?,?,?,?,?,?)", rows)


def seed_from_metadata(owner_address, daily_df):
    """Tạo dự án 2107 từ file metadata của dataset và nạp dữ liệu sản lượng."""
    meta = json.load(open(RAW_DIR / "2107_system_metadata.json"))
    s, site, mount = meta["System"], meta["Site"], meta["Mount"]["Mount 0"]
    if not get_project(SYSTEM_ID):
        add_project(SYSTEM_ID, s["public_name"], owner_address, s["power(kW DC)"],
                    location=site["location"], latitude=site["latitude"], longitude=site["longitude"],
                    tilt=mount["tilt"], azimuth=mount["azimuth"], started_on=s["started_on"][:10])
    load_production(SYSTEM_ID, daily_df)
    return get_project(SYSTEM_ID)
