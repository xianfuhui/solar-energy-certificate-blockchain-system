"""Chức năng 4: Phát hiện dữ liệu bất thường.

Hệ thống cơ bản : chỉ nhìn 1 nguồn (điện kế), cờ nếu vượt z-score 30 ngày gần nhất (phát hiện 'tăng đột biến').
Hệ thống đề xuất: kiểm tra chéo 3 oracle (luật độ lệch, ngưỡng học từ dữ liệu sạch)
                  + Isolation Forest trên đặc trưng chênh lệch giữa các oracle.
"""
import numpy as np, pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score
from config import SEED


# ---------------- Hệ thống cơ bản ----------------
def baseline_detect(r: pd.DataFrame, window=30, z=3.0) -> pd.Series:
    a = r["oracle_a"]
    hist = a.shift(1)                                  # chỉ dùng quá khứ
    mu, sd = hist.rolling(window, min_periods=10).mean(), hist.rolling(window, min_periods=10).std()
    return ((a - mu) / sd > z).fillna(False)


# ---------------- Hệ thống đề xuất ----------------
def _features(r):
    a, b, c = r.oracle_a, r.oracle_b, r.oracle_c
    f = pd.DataFrame(index=r.index)
    f["dev_ab"] = (a - b).abs() / r.consensus
    f["dev_ac"] = (a - c).abs() / r.consensus
    f["dev_bc"] = (b - c).abs() / r.consensus
    f["lr_ab"] = np.log((a + 1) / (b + 1))
    f["lr_ac"] = np.log((a + 1) / (c + 1))
    f["lr_bc"] = np.log((b + 1) / (c + 1))
    return f


class ProposedDetector:
    def __init__(self, q=0.995, margin=1.15, contamination=0.01):
        self.q, self.margin, self.cont = q, margin, contamination

    def fit(self, r_train):
        f = _features(r_train)
        # ngưỡng độ lệch học từ dữ liệu sạch (phân vị cao x biên an toàn)
        self.th = {k: f[k].quantile(self.q) * self.margin for k in ("dev_ab", "dev_ac", "dev_bc")}
        self.iso = IsolationForest(n_estimators=300, contamination=self.cont, random_state=SEED).fit(f)
        return self

    def predict(self, r) -> pd.DataFrame:
        f = _features(r)
        out = pd.DataFrame(index=r.index)
        out["rule_flag"] = (f.dev_ab > self.th["dev_ab"]) | (f.dev_ac > self.th["dev_ac"]) | (f.dev_bc > self.th["dev_bc"])
        out["iforest_flag"] = self.iso.predict(f) == -1
        out["ai_flagged"] = out.rule_flag | out.iforest_flag
        out["decision"] = np.where(out.ai_flagged, "REVIEW", "APPROVE")
        return out


def evaluate(y_true, y_pred, label):
    return dict(system=label, precision=precision_score(y_true, y_pred, zero_division=0),
                recall=recall_score(y_true, y_pred), f1=f1_score(y_true, y_pred),
                false_positives=int((y_pred & ~y_true).sum()), n=len(y_true))


def run_detection(r: pd.DataFrame):
    train, test = r[r.split == "train"], r[r.split == "test"]
    det = ProposedDetector().fit(train)
    res = det.predict(r)
    res["baseline_flag"] = baseline_detect(r)
    full = r.join(res)
    t = full[full.split == "test"]
    metrics = pd.DataFrame([evaluate(t.is_fraud, t.baseline_flag, "Cơ bản (1 oracle, z-score)"),
                            evaluate(t.is_fraud, t.ai_flagged, "Đề xuất (3 oracle + AI)")])
    by_type = (t[t.is_fraud].groupby("fraud_type")[["baseline_flag", "ai_flagged"]].mean().round(3))
    return full, metrics, by_type, det
