from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 检查原始数据和主脚本是否齐全；不修改输入数据。
required = [ROOT / name for name in ["题5_共享单车骑行_202401.csv", "analysis.py",
                                    "station_analysis.py", "membership_analysis.py"]]
missing = [str(p.name) for p in required if not p.exists()]
if missing:
    raise FileNotFoundError("缺少输入文件: " + ", ".join(missing))
# 摘要文件存在只表示已有输出，不代表它与当前数据版本一致。
summary = ROOT / "output" / "analysis_summary.json"
if summary.exists():
    print("output 子文件夹中已有分析结果；如数据或代码有变化，请重新运行 analysis.py。")
else:
    print("输入文件和分析脚本已就绪，请运行 analysis.py。")
