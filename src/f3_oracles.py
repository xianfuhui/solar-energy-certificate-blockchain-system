"""Chức năng 3: Mô phỏng Multi-oracle - 3 nguồn độc lập báo cáo sản lượng ngày (kWh).

 Oracle A  : điện kế đạt chuẩn doanh thu (meter_revenue_grade)  - số đo thật
 Oracle B  : tổng công suất AC của 24 inverter                   - số đo thật
 Oracle C  : mô hình vật lý từ bức xạ POA + nhiệt độ môi trường   - ước lượng độc lập
             (hồi quy tuyến tính, chỉ học từ tập huấn luyện sạch)
"""
import numpy as np, pandas as pd


def fit_oracle_c(daily: pd.DataFrame, split: pd.Series):
    tr = daily[split == "train"]
    X = np.c_[tr.poa_kwh_m2, tr.poa_kwh_m2 * tr.amb_temp, np.ones(len(tr))]
    coef, *_ = np.linalg.lstsq(X, tr.meter_kwh, rcond=None)
    return coef


def oracle_c(daily: pd.DataFrame, coef):
    X = np.c_[daily.poa_kwh_m2, daily.poa_kwh_m2 * daily.amb_temp, np.ones(len(daily))]
    return np.maximum(X @ coef, 0)


def build_oracle_readings(daily: pd.DataFrame, scenario: pd.DataFrame) -> pd.DataFrame:
    """Trả về bảng số đo 3 oracle sau khi áp kịch bản gian lận."""
    coef = fit_oracle_c(daily, scenario["split"])
    r = pd.DataFrame(index=daily.index)
    r["oracle_a"] = daily.meter_kwh * scenario.mul_a
    r["oracle_b"] = daily.inverter_kwh * scenario.mul_b
    r["oracle_c"] = oracle_c(daily, coef) * scenario.mul_c
    r["consensus"] = r[["oracle_a", "oracle_b", "oracle_c"]].median(axis=1)
    r["max_dev"] = (r[["oracle_a", "oracle_b", "oracle_c"]].sub(r.consensus, axis=0).abs()
                    .max(axis=1) / r.consensus)
    r = r.join(scenario[["split", "is_fraud", "fraud_type"]])
    return r.round(3)
