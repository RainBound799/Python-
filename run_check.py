from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
required = [ROOT / "题5_共享单车骑行_202401.csv", ROOT / "analysis.py"]
missing = [str(p.name) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError("缺少输入文件: " + ", ".join(missing))
summary = ROOT / "output" / "analysis_summary.json"
if summary.exists():
    print("已有分析结果，可直接查看 output/。")
else:
    print("输入文件和分析脚本已就绪，请运行 analysis.py。")
