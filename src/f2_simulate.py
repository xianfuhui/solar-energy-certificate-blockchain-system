"""Chức năng 2: Tạo dữ liệu mô phỏng - ngày bình thường và ngày gian lận.

Dữ liệu 'bình thường' là số đo thật của dataset 2107. Gian lận được chèn có kiểm soát vào tập kiểm thử,
mỗi ngày gian lận có nhãn + loại + hệ số nhân áp lên từng oracle (mul_a, mul_b, mul_c).
Tập huấn luyện (đầu chuỗi thời gian) giữ nguyên sạch để AI học hành vi bình thường.
"""
import numpy as np, pandas as pd
from config import SEED, TRAIN_FRACTION, FRAUD_RATE

FRAUD_TYPES = {
    # tên: (mô tả, số oracle bị sửa, khoảng hệ số nhân)
    "spike_single":   ("Tăng đột biến ở 1 oracle (x1.8-3.0)", 1, (1.8, 3.0)),
    "inflate_single": ("Phóng đại nhẹ ở 1 oracle (+15-30%)", 1, (1.15, 1.30)),
    "collusion":      ("2 oracle cùng bị sửa, oracle vật lý giữ nguyên (+25-50%)", 2, (1.25, 1.50)),
}


def simulate(daily: pd.DataFrame, seed=SEED, fraud_rate=FRAUD_RATE) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = len(daily)
    n_train = int(n * TRAIN_FRACTION)
    sc = pd.DataFrame(index=daily.index)
    sc["split"] = ["train"] * n_train + ["test"] * (n - n_train)
    sc["is_fraud"] = False
    sc["fraud_type"] = "none"
    for c in ("mul_a", "mul_b", "mul_c"):
        sc[c] = 1.0

    test_idx = np.arange(n_train, n)
    k = int(len(test_idx) * fraud_rate)
    chosen = rng.choice(test_idx, size=k, replace=False)
    types = list(FRAUD_TYPES)
    for i, pos in enumerate(chosen):
        t = types[i % len(types)]
        _, n_or, (lo, hi) = FRAUD_TYPES[t]
        # collusion chỉ sửa oracle A (điện kế) và B (inverter); C là mô hình từ cảm biến bức xạ độc lập
        pool = [0, 1, 2] if t != "collusion" else [0, 1]
        hit = rng.choice(pool, size=n_or, replace=False)
        for h in hit:
            sc.iloc[pos, sc.columns.get_loc(["mul_a", "mul_b", "mul_c"][h])] = rng.uniform(lo, hi)
        sc.iloc[pos, sc.columns.get_loc("is_fraud")] = True
        sc.iloc[pos, sc.columns.get_loc("fraud_type")] = t
    return sc
