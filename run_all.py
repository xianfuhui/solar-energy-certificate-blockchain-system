"""Chạy toàn bộ chức năng 1-5.   python run_all.py"""
import sys, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from web3 import Web3
from config import OUT_DIR, SYSTEM_ID
from src.data_prep import build_daily
from src import f1_projects as f1
from src.f2_simulate import simulate, FRAUD_TYPES
from src.f3_oracles import build_oracle_readings
from src.f4_detect import run_detection
from src import f5_issue as f5

pd.set_option("display.width", 200)
OUT_DIR.mkdir(exist_ok=True)

print("== Chức năng 1: Quản lý dự án ==")
daily = build_daily()
f5.compile_contract()
chain = f5.start_local_chain()
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
owner = w3.eth.accounts[1]                      # ví chủ dự án
project = f1.seed_from_metadata(owner, daily)
print(project); print(f1.production_summary(SYSTEM_ID))

print("\n== Chức năng 2: Dữ liệu mô phỏng ==")
sc = simulate(daily)
print(sc.groupby(["split", "fraud_type"]).size().unstack(fill_value=0))

print("\n== Chức năng 3: Multi-oracle ==")
readings = build_oracle_readings(daily, sc)
print(readings[["oracle_a", "oracle_b", "oracle_c", "consensus", "max_dev", "fraud_type"]].tail(8))
readings.to_csv(OUT_DIR / "oracle_readings.csv")

print("\n== Chức năng 4: Phát hiện bất thường ==")
full, metrics, by_type, det = run_detection(readings)
print(metrics.round(3).to_string(index=False)); print("\nTỷ lệ phát hiện theo loại gian lận:"); print(by_type)
full.to_csv(OUT_DIR / "detection_results.csv"); metrics.to_csv(OUT_DIR / "detection_metrics.csv", index=False)

print("\n== Chức năng 5: Cấp chứng chỉ trên blockchain ==")
test = full[full.split == "test"]
c = f5.deploy(w3, project, owner)
res = f5.issue_certificates(c, w3, test[~test.ai_flagged])               # luồng chuẩn: chỉ ngày AI đã duyệt
demo = f5.issue_certificates(c, w3, test[test.ai_flagged].head(10))      # thử cố tình gửi ngày bị gắn cờ
res = pd.concat([res, demo]); res.to_csv(OUT_DIR / "certificates.csv", index=False)
issued = res[res.status == "ISSUED"]
print(f"Đã cấp: {len(issued)} chứng chỉ, tổng {issued.energy_kwh.sum():,.0f} kWh "
      f"| on-chain: {c.functions.totalCertificates().call()} | chủ sở hữu: {len(c.functions.certificatesOf(owner).call())}")
print("Bị hợp đồng từ chối (thử gửi ngày bị gắn cờ):"); print(demo.reason.value_counts().to_string())
leak = issued[issued.is_fraud]
print(f"Gian lận lọt qua và được cấp chứng chỉ: {len(leak)} / {int(test.is_fraud.sum())} ngày gian lận")
print(leak.fraud_type.value_counts().to_string() if len(leak) else "")
print(f"Hợp đồng: {c.address}")

# Biểu đồ
fig, ax = plt.subplots(2, 1, figsize=(11, 7))
t = full[full.split == "test"]
ax[0].plot(t.index, t.oracle_a, lw=.7, label="Oracle A (điện kế)"); ax[0].plot(t.index, t.oracle_b, lw=.7, label="Oracle B (inverter)")
ax[0].plot(t.index, t.oracle_c, lw=.7, label="Oracle C (mô hình bức xạ)")
f = t[t.is_fraud]; ax[0].scatter(f.index, f.consensus, c="red", s=12, label="Ngày gian lận (nhãn)", zorder=3)
ax[0].set_ylabel("kWh/ngày"); ax[0].legend(fontsize=7, ncol=4); ax[0].set_title("3 oracle trong giai đoạn kiểm thử")
m = metrics.set_index("system")[["precision", "recall", "f1"]]; m.plot.bar(ax=ax[1], rot=0); ax[1].set_title("Hệ thống cơ bản vs đề xuất")
plt.tight_layout(); plt.savefig(OUT_DIR / "overview.png", dpi=130)
if chain: chain.terminate()
