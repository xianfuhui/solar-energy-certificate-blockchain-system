# Chứng chỉ năng lượng mặt trời – Dataset PVDAQ 2107 (chức năng 1–5)

## Chạy
    pip install -r requirements.txt && npm install
    export PVDAQ_RAW_DIR=/đường/dẫn/thư_mục_chứa_csv      # mặc định /home/claude/data
    PYTHONPATH=. python run_all.py

| File | Chức năng |
|---|---|
| src/f1_projects.py | 1. Quản lý dự án (SQLite): thêm/xem dự án, công suất, sản lượng |
| src/f2_simulate.py | 2. Dữ liệu bình thường + gian lận (spike, phóng đại nhẹ, 2 oracle thông đồng) |
| src/f3_oracles.py | 3. Multi-oracle: A điện kế, B tổng 24 inverter, C mô hình bức xạ POA |
| src/f4_detect.py | 4. Phát hiện bất thường: cơ bản (z-score) vs đề xuất (kiểm tra chéo + Isolation Forest) |
| contracts/EnergyCertificate.sol, src/f5_issue.py | 5. Cấp chứng chỉ (Solidity, chạy trên Ganache cục bộ) |

Kết quả ghi vào outputs/ (oracle_readings.csv, detection_results.csv, certificates.csv, overview.png).
Chưa làm: mục 6–10 (chống cấp trùng, chuyển nhượng, thu hồi, dashboard, thống kê).
