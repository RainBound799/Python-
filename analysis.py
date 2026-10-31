# -*- coding: utf-8 -*-
"""题目五：城市共享单车出行时空分析与调度优化"""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from station_analysis import analyze_stations
from membership_analysis import membership_preference, preference_chart

# 以脚本所在目录定位输入与输出，避免从其他目录运行时找不到文件。
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "题5_共享单车骑行_202401.csv"
# 在代码旁自动创建结果子文件夹；从其他工作目录启动时也保持一致。
OUT = ROOT / 'output'
FIG = OUT / 'figures'

# 优先加载支持中文的本地字体；不可用时回退到默认字体。
def font(size=22, bold=False):
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\arial.ttf"
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size, index=0)
            except Exception:
                pass
    return ImageFont.load_default()

F_TITLE, F_LABEL, F_SMALL = font(26), font(18), font(14)

# 创建白色画布，并返回用于绘制文字、坐标轴和图形的对象。
def canvas(w=1200, h=620):
    im = Image.new("RGB", (w, h), "white")
    return im, ImageDraw.Draw(im)

# 图表统一保存在 output/figures，统计表和摘要保存在 output。
def save(im, name):
    im.save(FIG / name, dpi=(180, 180))

# 绘制多条序列，自动按数据范围设置纵轴，并稀疏显示横轴标签。
def line_chart(x, ys, labels, title, name, colors=None):
    im, d = canvas()
    L, T, R, B = 80, 105, 1140, 540
    colors = colors or ["#2563eb", "#f97316", "#111827"]
    allv = np.concatenate([np.asarray(v, dtype=float) for v in ys])
    ymin, ymax = float(np.nanmin(allv)), float(np.nanmax(allv))
    pad = max((ymax-ymin)*.08, 1)
    ymin, ymax = ymin-pad, ymax+pad
    d.text((L, 20), title, fill="#111827", font=F_TITLE)
    d.line((L,T,L,B), fill="#777", width=2); d.line((L,B,R,B), fill="#777", width=2)
    for i in range(6):
        yy = B - i*(B-T)/5
        val = ymin + i*(ymax-ymin)/5
        d.line((L,yy,R,yy), fill="#e5e7eb", width=1)
        d.text((8, yy-8), f"{val:.0f}", fill="#555", font=F_SMALL)
    n = len(x)
    # 将数据索引和数值换算为画布上的像素坐标。
    def px(i): return L + (R-L)*i/max(n-1,1)
    def py(v): return B - (v-ymin)/(ymax-ymin)*(B-T)
    for arr, lab, col in zip(ys, labels, colors):
        pts=[(px(i),py(float(v))) for i,v in enumerate(arr)]
        d.line(pts, fill=col, width=3)
    step=max(1,n//12)
    for i in range(0,n,step):
        d.text((px(i)-8,B+8), str(x[i]), fill="#555", font=F_SMALL)
    lx=L
    for lab,col in zip(labels,colors):
        d.line((lx, T-25, lx+25, T-25), fill=col, width=4)
        d.text((lx+32,T-34), lab, fill="#333", font=F_SMALL); lx += 170
    save(im,name)

# 蓝色向右表示出发量，橙色向左表示到达量；左侧只表示方向，数量本身非负。
def bar_chart(labels, vals1, vals2, title, name, lab1="Departures", lab2="Arrivals"):
    im,d=canvas(1200,700); L,T,R,B=350,70,1140,610
    d.text((L,20),title,fill="#111827",font=F_TITLE)
    maxv=max(max(vals1),max(vals2),1)
    d.line((L,T,L,B),fill="#777",width=2)
    for i,(lab,a,b) in enumerate(zip(labels,vals1,vals2)):
        yy=T+i*(B-T)/len(labels)+8
        scale=(R-L-30)/maxv/2
        d.text((10,yy-10),str(lab)[:42],fill="#333",font=F_SMALL)
        d.rectangle((L,yy,L+a*scale,yy+12),fill="#2563eb")
        d.rectangle((L-b*scale,yy+16,L,yy+28),fill="#f97316")
    d.text((R-180,35),lab1,fill="#2563eb",font=F_SMALL); d.text((R-80,35),lab2,fill="#f97316",font=F_SMALL)
    save(im,name)

# 把星期与小时交叉统计映射为颜色深浅，并显示各单元的骑行次数。
def heatmap(mat, row_labels, col_labels, title, name):
    im,d=canvas(1200,620); L,T=120,80; cellw,cellh=42,52
    d.text((L,20),title,fill="#111827",font=F_TITLE)
    m=np.asarray(mat,dtype=float); mx=max(m.max(),1)
    for r in range(m.shape[0]):
        d.text((10,T+r*cellh+16),str(row_labels[r])[:12],fill="#333",font=F_SMALL)
        for c in range(m.shape[1]):
            val=m[r,c]; q=val/mx
            col=(255, int(245-150*q), int(230-190*q))
            x=L+c*cellw; y=T+r*cellh
            d.rectangle((x,y,x+cellw-2,y+cellh-2),fill=col)
            d.text((x+4,y+16),str(int(val)),fill="#222",font=F_SMALL)
    for c,lab in enumerate(col_labels):
        d.text((L+c*cellw+10,T+len(row_labels)*cellh+6),str(lab),fill="#333",font=F_SMALL)
    save(im,name)

# 将不同会员类别的小时需求并列绘制，便于观察时段差异。
def grouped_chart(df, title, name):
    # 按类别名称绑定颜色，避免数据列顺序变化后图例与柱形错配。
    styles = [('casual', '非会员 casual', '#2563eb'),
              ('member', '会员 member', '#f97316')]
    im,d = canvas(1500,780)
    L,T,R,B = 110,180,1430,660
    d.text((L,20),'不同会员类型的小时骑行量',fill='#111827',font=font(36))
    d.text((L,75),'2024年1月 · 按开始小时累计（次）',fill='#555',font=font(23))
    for j,(col,label,color) in enumerate(styles):
        x=L+j*420
        d.rectangle((x,126,x+28,146),fill=color)
        d.text((x+42,119),label,fill='#333',font=font(25))
    mx=max(df.max().max(),1)*1.08
    for tick in range(6):
        value=mx*tick/5; y=B-value/mx*(B-T)
        d.line((L,y,R,y),fill='#e5e7eb',width=2)
        d.text((L-15,y),f'{value:,.0f}',fill='#555',font=font(21),anchor='rm')
    for j,(col,label,color) in enumerate(styles):
        vals=df[col].reindex(range(24),fill_value=0).values
        for i,value in enumerate(vals):
            x=L+(i+.15)*(R-L)/24+j*20
            y=B-value/mx*(B-T)
            d.rectangle((x,y,x+17,B),fill=color)
    for i in range(24):
        d.text((L+(i+.5)*(R-L)/24,B+20),str(i),fill='#555',font=font(22),anchor='mm')
    d.text(((L+R)/2,727),'出发小时',fill='#555',font=font(24),anchor='mm')
    save(im,name)

# 使用正规方程求解岭回归；alpha 控制正则化强度。
def ridge_fit_predict(Xtr,ytr,Xte,alpha=10.0):
    Xtr=np.asarray(Xtr,float); Xte=np.asarray(Xte,float)
    # 补充常数列作为截距项，训练集和测试集采用相同的列结构。
    X1=np.c_[np.ones(len(Xtr)),Xtr]; X2=np.c_[np.ones(len(Xte)),Xte]
    # 对系数施加 L2 惩罚，但不惩罚截距项；用线性方程求解代替显式求逆。
    A=X1.T@X1 + alpha*np.eye(X1.shape[1]); A[0,0]-=alpha
    beta=np.linalg.solve(A, X1.T@ytr)
    # 骑行量不能为负，将模型的负预测值截断为零。
    return np.maximum(0, X2@beta)

# MAE 衡量平均绝对误差，RMSE 对大误差更敏感；R² 越接近 1，拟合效果越好。
def metric(y,p):
    e=np.asarray(y)-np.asarray(p)
    return {"MAE":float(np.mean(np.abs(e))),"RMSE":float(np.sqrt(np.mean(e**2))),"R2":float(1-np.sum(e**2)/np.sum((np.asarray(y)-np.mean(y))**2))}

def main():
    # 首次运行自动创建目录，重复运行复用目录并更新同名结果。
    FIG.mkdir(parents=True, exist_ok=True)
    # 读取原始数据；utf-8-sig 同时兼容带有 BOM 的 UTF-8 文件。
    raw=pd.read_csv(DATA,encoding="utf-8-sig",
                    dtype={'start_station_id':'string','end_station_id':'string'})
    raw_rows=len(raw); raw_dupes=int(raw.duplicated(subset=["ride_id"]).sum())
    # 无法解析的时间转为缺失值，再用起止时间差重新计算骑行分钟数。
    for c in ["started_at","ended_at"]: raw[c]=pd.to_datetime(raw[c],errors="coerce")
    raw["duration_min"]=(raw.ended_at-raw.started_at).dt.total_seconds()/60
    # 保留编号和时间完整、时长在 0.5 至 1440 分钟之间的记录（包含边界）。
    valid=(raw.ride_id.notna()&raw.started_at.notna()&raw.ended_at.notna()&raw.duration_min.between(.5,1440))
    # 重复骑行编号只保留首次出现的记录。
    valid &= ~raw.duplicated(subset=["ride_id"],keep="first")
    df=raw.loc[valid].copy()
    # 提取时间特征；星期编号从周一的 0 到周日的 6。
    df["hour"]=df.started_at.dt.hour; df["weekday_num"]=df.started_at.dt.dayofweek
    df["weekday"]=df.started_at.dt.day_name(); df["is_weekend"]=(df.weekday_num>=5).astype(int)
    # 缺失站点统一归入未知类别，以保留时间分析样本；未知类别不是真实调度地点。
    df["start_station_id"]=df.start_station_id.fillna("UNKNOWN"); df["end_station_id"]=df.end_station_id.fillna("UNKNOWN")
    df["start_station_name"]=df.start_station_name.fillna("Unknown station"); df["end_station_name"]=df.end_station_name.fillna("Unknown station")
    # 汇总清洗前后样本量、时长分位数和原始缺失量，供报告核对。
    cleaning={"raw_rows":raw_rows,"duplicate_ride_ids":raw_dupes,"valid_rows":len(df),"removed_rows":raw_rows-len(df),"valid_rate":len(df)/raw_rows,
      "duration_min_median":df.duration_min.median(),"duration_min_mean":df.duration_min.mean(),"duration_min_p95":df.duration_min.quantile(.95),
      "start_station_missing_raw":int(raw.start_station_id.isna().sum()),"end_station_missing_raw":int(raw.end_station_id.isna().sum()),
      "end_coordinate_missing_raw":int(raw.end_lat.isna().sum())}
    pd.DataFrame([cleaning]).to_csv(OUT/"cleaning_summary.csv",index=False,encoding="utf-8-sig")
    # 按出发小时汇总骑行量，并补齐 0 至 23 时，空缺小时记为零。
    hourly=df.groupby("hour").size().reindex(range(24),fill_value=0); hourly.rename("rides").to_csv(OUT/"hourly_demand.csv",encoding="utf-8-sig")
    line_chart(list(range(24)),[hourly.values],["Trips"],"Hourly bike trips in January 2024","01_hourly_demand.png")
    # 固定星期顺序；这里统计的是月内总量，未按各星期出现的天数归一化。
    order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    heat=df.pivot_table(index="weekday",columns="hour",values="ride_id",aggfunc="count",fill_value=0).reindex(order,fill_value=0).reindex(columns=range(24),fill_value=0)
    heat.to_csv(OUT/"weekday_hour_heatmap.csv",encoding="utf-8-sig"); heatmap(heat.values,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],range(24),"Trips by weekday and start hour","02_weekday_hour_heatmap.png")
    # 图3按已知站点的流入+流出排序；另导出分日期、小时、车型的净流出和调度参考。
    station=analyze_stations(df,OUT)
    # 出发按开始小时统计，到达按结束小时统计；全网净流量不能等同于单站库存缺口。
    dep_h=df.groupby("hour").size().rename("departures"); arr_h=df.groupby(df.ended_at.dt.hour).size().rename("arrivals"); flow=pd.concat([dep_h,arr_h],axis=1).fillna(0).reindex(range(24),fill_value=0); flow["net_outflow"]=flow.departures-flow.arrivals; flow.to_csv(OUT/"hourly_net_flow.csv",encoding="utf-8-sig"); line_chart(list(range(24)),[flow.net_outflow.values],["Net outflow"],"System net flow by hour","04_hourly_net_flow.png",["#7c3aed"])
    # 交叉统计会员与车型组合，并进一步比较会员类别的小时分布。
    preference = membership_preference(df)
    preference[['member_casual', 'rideable_type', 'rides']].to_csv(OUT/'user_vehicle_profile.csv', index=False, encoding='utf-8-sig')
    preference.to_csv(OUT/'user_vehicle_preference.csv', index=False, encoding='utf-8-sig')
    preference_chart(preference, FIG/'09_membership_vehicle_preference.png', font)
    memb=df.pivot_table(index="hour",columns="member_casual",values="ride_id",aggfunc="count",fill_value=0).reindex(range(24),fill_value=0); grouped_chart(memb,"Hourly demand by membership type","05_membership_hourly.png")
    # 聚合为连续小时序列，按时间先后划分前 80% 训练、后 20% 测试，避免随机切分。
    ts=df.groupby(df.started_at.dt.floor("h")).size().rename("demand").asfreq("h",fill_value=0).to_frame(); ts["hour"]=ts.index.hour; ts["weekday_num"]=ts.index.dayofweek; ts["is_weekend"]=(ts.weekday_num>=5).astype(int); ts["day"]=ts.index.day; ts["trend"]=np.arange(len(ts)); n=len(ts); split=int(n*.8); train,test=ts.iloc[:split],ts.iloc[split:]
    # 构造 34 列特征：24 列小时独热编码、7 列星期独热编码和 3 列数值特征。
    def features(x):
        a=np.zeros((len(x),24+7+3))
        for i,(h,wk,weekend,day,tr) in enumerate(zip(x.hour,x.weekday_num,x.is_weekend,x.day,x.trend)):
            a[i,int(h)]=1; a[i,24+int(wk)]=1; a[i,31:]=[weekend,day,tr/len(ts)]
        return a
    Xtr,Xte=features(train),features(test); ytr,yte=train.demand.values,test.demand.values
    # 时段+星期均值基线
    # 基线均值只用训练集计算；测试时未见过的组合回退到训练集整体均值。
    means=train.groupby(["hour","weekday_num"]).demand.mean(); pred_base=np.array([means.get((h,w),train.demand.mean()) for h,w in zip(test.hour,test.weekday_num)])
    # 在同一测试集比较两种方法；误差越小越好，R² 也可能为负。
    pred_ridge=ridge_fit_predict(Xtr,ytr,Xte); metrics=[{"model":"seasonal_mean","MAE":metric(yte,pred_base)["MAE"],"RMSE":metric(yte,pred_base)["RMSE"],"R2":metric(yte,pred_base)["R2"]},{"model":"ridge","MAE":metric(yte,pred_ridge)["MAE"],"RMSE":metric(yte,pred_ridge)["RMSE"],"R2":metric(yte,pred_ridge)["R2"]}]
    pd.DataFrame(metrics).to_csv(OUT/"model_metrics.csv",index=False,encoding="utf-8-sig"); pd.DataFrame({"actual":yte,"seasonal_mean":pred_base,"ridge":pred_ridge},index=test.index).to_csv(OUT/"model_predictions.csv",encoding="utf-8-sig")
    line_chart(list(test.index.strftime("%m-%d %H")), [yte,pred_base,pred_ridge],["Actual","Seasonal mean","Ridge"],"Hourly demand prediction on chronological test set","06_model_prediction.png")
    # 分别提取净流出和净流入靠前的类别；具体站点建议需排除未知站点。
    top_out=station.sort_values("net_outflow",ascending=False).head(5)[["station_name","departures","arrivals","net_outflow"]]; top_in=station.sort_values("net_outflow").head(5)[["station_name","departures","arrivals","net_outflow"]]
    # 集中导出报告所需指标，确保图表、统计表与文字引用来源一致。
    summary={"cleaning":cleaning,"peak_hour":int(hourly.idxmax()),"peak_hour_trips":int(hourly.max()),"peak_weekday_hour":{"weekday":str(heat.stack().idxmax()[0]),"hour":int(heat.stack().idxmax()[1]),"trips":int(heat.stack().max())},"member_share":{str(k):float(v) for k,v in df.member_casual.value_counts(normalize=True).items()},"vehicle_share":{str(k):float(v) for k,v in df.rideable_type.value_counts(normalize=True).items()},"top_outflow_stations":top_out.to_dict(orient="records"),"top_inflow_stations":top_in.to_dict(orient="records"),"model_metrics":metrics,"best_model":min(metrics,key=lambda x:x["RMSE"])["model"]}
    summary['membership_vehicle_preference'] = json.loads(preference.to_json(orient='records'))
    electric_share = preference.loc[preference.rideable_type.eq('electric_bike')].set_index('member_casual').within_membership_share
    difference = float((electric_share['casual'] - electric_share['member']) * 100)
    summary['casual_minus_member_electric_percentage_points'] = difference if math.isfinite(difference) else None
    (OUT/"analysis_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(summary,ensure_ascii=False,indent=2))
# 仅在直接运行脚本时执行完整分析，作为模块导入时不自动运行主流程。
if __name__=="__main__": main()

