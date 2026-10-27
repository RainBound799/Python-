from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
# 检查原始数据和主脚本是否齐全；不修改输入数据。
required = [ROOT / "题5_共享单车骑行_202401.csv", ROOT / "analysis.py", ROOT / "station_analysis.py"]
missing = [str(p.name) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError("缺少输入文件: " + ", ".join(missing))
# 摘要文件存在只表示已有输出，不代表它与当前数据版本一致。
summary = ROOT / "output" / "analysis_summary.json"
if summary.exists():
    print("已有分析结果，可直接查看 output/。")
else:
    print("输入文件和分析脚本已就绪，请运行 analysis.py。")
