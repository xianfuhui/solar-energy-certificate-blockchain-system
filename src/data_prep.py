"""Đọc dataset PVDAQ 2107 và gộp thành bảng sản lượng điện theo ngày (kWh)."""
import pandas as pd
import numpy as np
from config import RAW_DIR, DATA_DIR

START, END = "2018-12-15", "2023-09-30"   # khoảng dữ liệu đầy đủ của hệ thống 2107


def _read(name, usecols=None):
    return pd.read_csv(RAW_DIR / name, usecols=usecols, parse_dates=["measured_on"], index_col="measured_on")


def build_daily(force=False):
    out = DATA_DIR / "daily_2107.csv"
    if out.exists() and not force:
        return pd.read_csv(out, parse_dates=["date"], index_col="date")

    meter = _read("2107_meter_15m_data.csv").iloc[:, 0]                       # kW @15 phút
    inv = _read("2107_electrical_data_v1.csv",
                usecols=lambda c: c == "measured_on" or "ac_power" in c)       # kW @5 phút, 24 inverter
    poa = _read("2107_irradiance_data.csv").iloc[:, 0]                         # W/m2
    amb = _read("2107_environment_data.csv")["ambient_temperature_o_149575"]   # °C

    inv15 = inv.sum(axis=1, min_count=1).resample("15min").mean()
    meter15 = meter.resample("15min").mean()
    poa15 = poa.resample("15min").mean()
    amb15 = amb.resample("15min").mean()

    df = pd.DataFrame({
        "meter_kwh": meter15.fillna(0).resample("D").sum() / 4,
        "inverter_kwh": inv15.fillna(0).resample("D").sum() / 4,
        "poa_kwh_m2": poa15.fillna(0).resample("D").sum() / 4 / 1000,
        "amb_temp": amb15.resample("D").mean(),
        "n_meter": meter15.resample("D").count(),
        "n_inv": inv15.resample("D").count(),
    })
    midday = poa15.between_time("10:00", "14:00").resample("D").count()
    df["n_poa_midday"] = midday.reindex(df.index).fillna(0)
    ok = (df.n_meter >= 92) & (df.n_inv >= 92) & (df.n_poa_midday >= 14) & (df.meter_kwh > 100)
    df = df[ok].loc[START:END].drop(columns=["n_meter", "n_inv", "n_poa_midday"])
    r = df.inverter_kwh / df.meter_kwh
    df = df[(r > 0.9) & (r < 1.15)]
    df = df[df.poa_kwh_m2 <= 10]                       # loại ngày cảm biến bức xạ lỗi (vd. 18 kWh/m2)
    df["amb_temp"] = ((df.amb_temp - 32) * 5 / 9)      # dữ liệu gốc là °F -> °C
    df["amb_temp"] = df["amb_temp"].fillna(df["amb_temp"].median())
    df.index.name = "date"
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    df.round(3).to_csv(out)
    return df


if __name__ == "__main__":
    d = build_daily(force=True)
    print(d.describe().round(2)); print(len(d), "ngày hợp lệ")
