"""Chức năng 5: Cấp chứng chỉ năng lượng trên blockchain (Solidity).

Luồng: dữ liệu 3 oracle -> AI (f4) -> yêu cầu cấp -> smart contract kiểm tra lại điều kiện -> mint chứng chỉ.
Chỉ ngày được AI duyệt (APPROVE) mới được gửi lên hợp đồng; ngày REVIEW bị chặn ngay từ phía hợp đồng nếu cố gửi.
"""
import json, subprocess, time, socket
from pathlib import Path
import pandas as pd
from web3 import Web3
from config import ROOT, SYSTEM_ID

BUILD = ROOT / "contracts" / "build" / "EnergyCertificate.json"
TOLERANCE_BPS = 3500   # tuyến phòng thủ thứ hai trên chuỗi: lệch > 35% so với trung vị là bị từ chối


def compile_contract():
    subprocess.run(["node", str(ROOT / "scripts" / "compile.js")], check=True, cwd=ROOT)


def start_local_chain(port=8545):
    """Khởi động Ganache (chuỗi cục bộ) nếu chưa chạy."""
    def up():
        with socket.socket() as s:
            return s.connect_ex(("127.0.0.1", port)) == 0
    if up():
        return None
    p = subprocess.Popen(["npx", "ganache", "--wallet.deterministic", "-p", str(port), "--logging.quiet"],
                         cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        if up():
            time.sleep(1)
            return p
        time.sleep(0.5)
    raise RuntimeError("Không khởi động được Ganache")


def deploy(w3, project, owner_addr):
    art = json.load(open(BUILD))
    admin = w3.eth.accounts[0]
    C = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
    addr = w3.eth.wait_for_transaction_receipt(C.constructor(TOLERANCE_BPS).transact({"from": admin})).contractAddress
    c = w3.eth.contract(address=addr, abi=art["abi"])
    w3.eth.wait_for_transaction_receipt(
        c.functions.registerProject(SYSTEM_ID, owner_addr, int(project["capacity_kw"])).transact({"from": admin}))
    return c


def _to_int_date(ts):
    return int(ts.strftime("%Y%m%d"))


def issue_certificates(c, w3, full: pd.DataFrame, days=None):
    """Gửi yêu cầu cấp cho từng ngày; trả bảng kết quả (đã cấp / bị từ chối + lý do)."""
    admin = w3.eth.accounts[0]
    rows = []
    for ts, r in (full if days is None else full.loc[days]).iterrows():
        readings = [int(round(r.oracle_a * 1000)), int(round(r.oracle_b * 1000)), int(round(r.oracle_c * 1000))]
        flagged = bool(r.ai_flagged)
        rec = dict(date=ts.strftime("%Y-%m-%d"), oracle_a=r.oracle_a, oracle_b=r.oracle_b, oracle_c=r.oracle_c,
                   ai_flagged=flagged, is_fraud=bool(r.is_fraud), fraud_type=r.fraud_type)
        try:
            h = c.functions.issueCertificate(SYSTEM_ID, _to_int_date(ts), readings, flagged).transact({"from": admin})
            rcpt = w3.eth.wait_for_transaction_receipt(h)
            ev = c.events.CertificateIssued().process_receipt(rcpt)[0]["args"]
            rec.update(status="ISSUED", cert_id=ev["certId"], energy_kwh=ev["energyWh"] / 1000, tx=h.hex(), reason="")
        except Exception as e:                      # hợp đồng revert
            msg = str(e)
            reason = next((k for k in ("flagged by AI", "oracle mismatch", "exceeds capacity", "zero energy")
                           if k in msg), msg[:80])
            rec.update(status="REJECTED", cert_id=None, energy_kwh=None, tx="", reason=reason)
        rows.append(rec)
    return pd.DataFrame(rows)
