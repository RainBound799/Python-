# -*- coding: utf-8 -*-
"""题目五：城市共享单车出行时空分析与调度优化"""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "题5_共享单车骑行_202401.csv"
OUT = ROOT / "output"
FIG = OUT / "figures"
OUT.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

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

def canvas(w=1200, h=620):
    im = Image.new("RGB", (w, h), "white")
    return im, ImageDraw.Draw(im)

def save(im, name):
    im.save(FIG / name, dpi=(180, 180))

def line_chart(x, ys, labels, title, name, colors=None):
    im, d = canvas()
    L, T, R, B = 80, 70, 1140, 540
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

def grouped_chart(df, title, name):
    hours=range(24); im,d=canvas(); L,T,R,B=75,70,1140,540
    d.text((L,20),title,fill="#111827",font=F_TITLE)
    mx=max(df.max().max(),1)
    for j,col in enumerate(df.columns):
        vals=df[col].reindex(hours,fill_value=0).values
        for i,v in enumerate(vals):
            x=L+i*(R-L)/24+j*10
            y=B-v/mx*(B-T)
            d.rectangle((x,y,x+8,B),fill=["#2563eb","#f97316","#16a34a"][j%3])
    for i in range(0,24,2): d.text((L+i*(R-L)/24-5,B+8),str(i),fill="#555",font=F_SMALL)
    save(im,name)

def ridge_fit_predict(Xtr,ytr,Xte,alpha=10.0):
    Xtr=np.asarray(Xtr,float); Xte=np.asarray(Xte,float)
    X1=np.c_[np.ones(len(Xtr)),Xtr]; X2=np.c_[np.ones(len(Xte)),Xte]
    A=X1.T@X1 + alpha*np.eye(X1.shape[1]); A[0,0]-=alpha
    beta=np.linalg.solve(A, X1.T@ytr)
    return np.maximum(0, X2@beta)

def metric(y,p):
    e=np.asarray(y)-np.asarray(p)
    return {"MAE":float(np.mean(np.abs(e))),"RMSE":float(np.sqrt(np.mean(e**2))),"R2":float(1-np.sum(e**2)/np.sum((np.asarray(y)-np.mean(y))**2))}

def main():
    raw=pd.read_csv(DATA,encoding="utf-8-sig")
    raw_rows=len(raw); raw_dupes=int(raw.duplicated(subset=["ride_id"]).sum())
    for c in ["started_at","ended_at"]: raw[c]=pd.to_datetime(raw[c],errors="coerce")
    raw["duration_min"]=(raw.ended_at-raw.started_at).dt.total_seconds()/60
    valid=(raw.ride_id.notna()&raw.started_at.notna()&raw.ended_at.notna()&raw.duration_min.between(.5,1440))
    valid &= ~raw.duplicated(subset=["ride_id"],keep="first")
    df=raw.loc[valid].copy()
    df["hour"]=df.started_at.dt.hour; df["weekday_num"]=df.started_at.dt.dayofweek
    df["weekday"]=df.started_at.dt.day_name(); df["is_weekend"]=(df.weekday_num>=5).astype(int)
    df["start_station_id"]=df.start_station_id.fillna("UNKNOWN"); df["end_station_id"]=df.end_station_id.fillna("UNKNOWN")
    df["start_station_name"]=df.start_station_name.fillna("Unknown station"); df["end_station_name"]=df.end_station_name.fillna("Unknown station")
    cleaning={"raw_rows":raw_rows,"duplicate_ride_ids":raw_dupes,"valid_rows":len(df),"removed_rows":raw_rows-len(df),"valid_rate":len(df)/raw_rows,
      "duration_min_median":df.duration_min.median(),"duration_min_mean":df.duration_min.mean(),"duration_min_p95":df.duration_min.quantile(.95),
      "start_station_missing_raw":int(raw.start_station_id.isna().sum()),"end_station_missing_raw":int(raw.end_station_id.isna().sum()),
      "end_coordinate_missing_raw":int(raw.end_lat.isna().sum())}
    pd.DataFrame([cleaning]).to_csv(OUT/"cleaning_summary.csv",index=False,encoding="utf-8-sig")
    hourly=df.groupby("hour").size().reindex(range(24),fill_value=0); hourly.rename("rides").to_csv(OUT/"hourly_demand.csv",encoding="utf-8-sig")
    line_chart(list(range(24)),[hourly.values],["Trips"],"Hourly bike trips in January 2024","01_hourly_demand.png")
    order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    heat=df.pivot_table(index="weekday",columns="hour",values="ride_id",aggfunc="count",fill_value=0).reindex(order,fill_value=0).reindex(columns=range(24),fill_value=0)
    heat.to_csv(OUT/"weekday_hour_heatmap.csv",encoding="utf-8-sig"); heatmap(heat.values,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],range(24),"Trips by weekday and start hour","02_weekday_hour_heatmap.png")
    starts=df.groupby(["start_station_id","start_station_name"]).size().rename("departures").reset_index().rename(columns={"start_station_id":"station_id","start_station_name":"station_name"})
    ends=df.groupby(["end_station_id","end_station_name"]).size().rename("arrivals").reset_index().rename(columns={"end_station_id":"station_id","end_station_name":"station_name"})
    station=starts.merge(ends[["station_id","arrivals"]],on="station_id",how="outer").fillna(0); station["net_outflow"]=station.departures-station.arrivals; station["total_activity"]=station.departures+station.arrivals; station["imbalance_index"]=station.net_outflow.abs()/station.total_activity.replace(0,np.nan); station=station.sort_values("total_activity",ascending=False)
    station.to_csv(OUT/"station_supply_demand.csv",index=False,encoding="utf-8-sig")
    top=station.head(15).sort_values("departures"); bar_chart(top.station_name.tolist(),top.departures.tolist(),top.arrivals.tolist(),"Top 15 stations: departures vs arrivals","03_top_stations_flow.png")
    dep_h=df.groupby("hour").size().rename("departures"); arr_h=df.groupby(df.ended_at.dt.hour).size().rename("arrivals"); flow=pd.concat([dep_h,arr_h],axis=1).fillna(0).reindex(range(24),fill_value=0); flow["net_outflow"]=flow.departures-flow.arrivals; flow.to_csv(OUT/"hourly_net_flow.csv",encoding="utf-8-sig"); line_chart(list(range(24)),[flow.net_outflow.values],["Net outflow"],"System net flow by hour","04_hourly_net_flow.png",["#7c3aed"])
    profile=df.groupby(["member_casual","rideable_type"]).size().rename("rides").reset_index(); profile.to_csv(OUT/"user_vehicle_profile.csv",index=False,encoding="utf-8-sig")
    memb=df.pivot_table(index="hour",columns="member_casual",values="ride_id",aggfunc="count",fill_value=0).reindex(range(24),fill_value=0); grouped_chart(memb,"Hourly demand by membership type","05_membership_hourly.png")
    ts=df.groupby(df.started_at.dt.floor("h")).size().rename("demand").asfreq("h",fill_value=0).to_frame(); ts["hour"]=ts.index.hour; ts["weekday_num"]=ts.index.dayofweek; ts["is_weekend"]=(ts.weekday_num>=5).astype(int); ts["day"]=ts.index.day; ts["trend"]=np.arange(len(ts)); n=len(ts); split=int(n*.8); train,test=ts.iloc[:split],ts.iloc[split:]
    def features(x):
        a=np.zeros((len(x),24+7+3))
        for i,(h,wk,weekend,day,tr) in enumerate(zip(x.hour,x.weekday_num,x.is_weekend,x.day,x.trend)):
            a[i,int(h)]=1; a[i,24+int(wk)]=1; a[i,31:]=[weekend,day,tr/len(ts)]
        return a
    Xtr,Xte=features(train),features(test); ytr,yte=train.demand.values,test.demand.values
    # 时段+星期均值基线
    means=train.groupby(["hour","weekday_num"]).demand.mean(); pred_base=np.array([means.get((h,w),train.demand.mean()) for h,w in zip(test.hour,test.weekday_num)])
    pred_ridge=ridge_fit_predict(Xtr,ytr,Xte); metrics=[{"model":"seasonal_mean","MAE":metric(yte,pred_base)["MAE"],"RMSE":metric(yte,pred_base)["RMSE"],"R2":metric(yte,pred_base)["R2"]},{"model":"ridge","MAE":metric(yte,pred_ridge)["MAE"],"RMSE":metric(yte,pred_ridge)["RMSE"],"R2":metric(yte,pred_ridge)["R2"]}]
    pd.DataFrame(metrics).to_csv(OUT/"model_metrics.csv",index=False,encoding="utf-8-sig"); pd.DataFrame({"actual":yte,"seasonal_mean":pred_base,"ridge":pred_ridge},index=test.index).to_csv(OUT/"model_predictions.csv",encoding="utf-8-sig")
    line_chart(list(test.index.strftime("%m-%d %H")), [yte,pred_base,pred_ridge],["Actual","Seasonal mean","Ridge"],"Hourly demand prediction on chronological test set","06_model_prediction.png")
    top_out=station.sort_values("net_outflow",ascending=False).head(5)[["station_name","departures","arrivals","net_outflow"]]; top_in=station.sort_values("net_outflow").head(5)[["station_name","departures","arrivals","net_outflow"]]
    summary={"cleaning":cleaning,"peak_hour":int(hourly.idxmax()),"peak_hour_trips":int(hourly.max()),"peak_weekday_hour":{"weekday":str(heat.stack().idxmax()[0]),"hour":int(heat.stack().idxmax()[1]),"trips":int(heat.stack().max())},"member_share":{str(k):float(v) for k,v in df.member_casual.value_counts(normalize=True).items()},"vehicle_share":{str(k):float(v) for k,v in df.rideable_type.value_counts(normalize=True).items()},"top_outflow_stations":top_out.to_dict(orient="records"),"top_inflow_stations":top_in.to_dict(orient="records"),"model_metrics":metrics,"best_model":min(metrics,key=lambda x:x["RMSE"])["model"]}
    (OUT/"analysis_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=="__main__": main()

