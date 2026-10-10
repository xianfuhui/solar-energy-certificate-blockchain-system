"""Cấu hình chung cho toàn bộ dự án."""
from pathlib import Path
import os

ROOT = Path(__file__).parent
# Thư mục chứa các file CSV của dataset (giải nén từ archive.zip). Có thể ghi đè bằng biến môi trường.
RAW_DIR = Path(os.environ.get("PVDAQ_RAW_DIR", "/home/claude/data"))
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"
DB_PATH = DATA_DIR / "projects.db"

SYSTEM_ID = 2107
SEED = 42

# Khoảng thời gian dùng để huấn luyện (dữ liệu sạch) / kiểm thử (có chèn gian lận)
TRAIN_FRACTION = 0.6

# Ngưỡng kiểm tra chéo giữa các oracle (độ lệch tương đối so với trung vị)
ORACLE_TOLERANCE = 0.15
# Tỷ lệ ngày bị chèn gian lận trong tập kiểm thử
FRAUD_RATE = 0.20
