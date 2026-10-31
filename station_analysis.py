"""高活动站点分析：端点事件、分时净流出和分车型调度参考。

净流出 = departures - arrivals，正值代表骑走多，负值代表骑入多。
所有计数来自骑行事件，不包括调度车搬运，也不是实际库存或未满足需求。
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

START = pd.Timestamp('2024-01-01')
STOP = pd.Timestamp('2024-02-01')
TYPES = ['electric_bike', 'classic_bike']
WINDOWS = [(0, 7, '00–07'), (7, 10, '07–10'), (10, 16, '10–16'),
           (16, 20, '16–20'), (20, 24, '20–24')]


def endpoint_events(df):
    """分别读取起点/终点；一端缺失不妨碍另一端参加已知站点统计。"""
    pieces = []
    for prefix, time_col, direction in [('start', 'started_at', 'departures'),
                                         ('end', 'ended_at', 'arrivals')]:
        part = df[[prefix+'_station_id', prefix+'_station_name', time_col,
                   'rideable_type']].copy()
        part.columns = ['station_id', 'station_name', 'event_time', 'rideable_type']
        part['station_id'] = part.station_id.astype('string').str.strip()
        part = part.loc[part.station_id.notna() & ~part.station_id.isin(['UNKNOWN', ''])]
        part['direction'] = direction
        pieces.append(part)
    all_events = pd.concat(pieces, ignore_index=True)
    in_month = all_events.event_time.ge(START) & all_events.event_time.lt(STOP)
    events = all_events.loc[in_month].copy()
    events['date'] = events.event_time.dt.normalize()
    events['hour'] = events.event_time.dt.hour
    events['day_type'] = np.where(events.event_time.dt.dayofweek.lt(5), 'weekday', 'weekend')
    audit = {
        'period_start': str(START), 'period_end_exclusive': str(STOP),
        'known_endpoint_events_in_month': len(events),
        'known_endpoint_events_outside_month': int((~in_month).sum()),
        'valid_trip_count': len(df),
        'unknown_start_count': int(df.start_station_id.isin(['UNKNOWN']).sum()),
        'unknown_end_count': int(df.end_station_id.isin(['UNKNOWN']).sum()),
        'weekday_days': 23, 'weekend_days': 8, 'all_days': 31,
        'net_definition': 'departures - arrivals',
    }
    return events, audit


def flow_counts(events, keys, full_index=None):
    """在固定索引上补零，让无骑行的日期/时段也进入平均值的分母。"""
    counts = events.groupby(keys+['direction']).size().unstack('direction', fill_value=0)
    counts = counts.reindex(columns=['departures', 'arrivals'], fill_value=0)
    if full_index is not None:
        counts = counts.reindex(full_index, fill_value=0)
    counts = counts.astype(int)
    counts['total_activity'] = counts.departures + counts.arrivals
    counts['net_outflow'] = counts.departures - counts.arrivals
    return counts.reset_index()


def analyze_stations(df, out):
    """返回全站点汇总，并将前15站的精确计数、日均值和调度比例导出。"""
    out = Path(out)
    events, audit = endpoint_events(df)
    # 同一编号可能有名称变体；采用出现次数最多的名称，保证一站一行。
    names = (events.groupby(['station_id', 'station_name']).size().rename('count').reset_index()
             .sort_values(['count', 'station_name'], ascending=[False, True])
             .drop_duplicates('station_id')[['station_id', 'station_name']])
    station = flow_counts(events, ['station_id']).merge(names, on='station_id', how='left')
    station['station_name'] = station.station_name.fillna(station.station_id)
    station['imbalance_index'] = station.net_outflow.abs()/station.total_activity
    station = station.sort_values(['total_activity', 'station_id'], ascending=[False, True]).reset_index(drop=True)
    station.to_csv(out/'station_supply_demand.csv', index=False, encoding='utf-8-sig')
    top = station.head(15).copy()
    top.insert(0, 'rank', range(1, len(top)+1))
    top['activity_share_all_known'] = top.total_activity / station.total_activity.sum()
    top['activity_share_top15'] = top.total_activity / top.total_activity.sum()
    top['activity_per_day'] = top.total_activity / 31
    ids = top.station_id.tolist()
    ev = events.loc[events.station_id.isin(ids)]
    dates = pd.date_range(START, STOP-pd.Timedelta(days=1), freq='D')
    # 全月份的每一天、每一小时、每一车型均有一行，保留真实日期变化。
    idx = pd.MultiIndex.from_product([ids, dates, range(24), TYPES],
                                    names=['station_id', 'date', 'hour', 'rideable_type'])
    detail = flow_counts(ev, ['station_id', 'date', 'hour', 'rideable_type'], idx)
    detail['day_type'] = np.where(detail.date.dt.dayofweek.lt(5), 'weekday', 'weekend')
    detail.to_csv(out/'top_station_date_hour_vehicle.csv', index=False, encoding='utf-8-sig')
    metrics = ['departures', 'arrivals', 'total_activity', 'net_outflow']
    profiles = []
    for label, days in [('all', 31), ('weekday', 23), ('weekend', 8)]:
        subset = detail if label == 'all' else detail.loc[detail.day_type.eq(label)]
        agg = subset.groupby(['station_id', 'hour', 'rideable_type'])[metrics].sum().reset_index()
        agg['day_type'] = label
        agg['n_days'] = days
        for col in metrics:
            agg[col+'_per_day'] = agg[col]/days
        profiles.append(agg)
    profile = pd.concat(profiles, ignore_index=True)
    profile.to_csv(out/'top_station_hourly_vehicle.csv', index=False, encoding='utf-8-sig')
    hourly = profile.groupby(['station_id', 'day_type', 'hour'])[metrics].sum().reset_index()
    hourly['n_days'] = hourly.day_type.map({'all':31, 'weekday':23, 'weekend':8})
    for col in metrics:
        hourly[col+'_per_day'] = hourly[col]/hourly.n_days
    hourly.to_csv(out/'top_station_hourly_flow.csv', index=False, encoding='utf-8-sig')
    daily = detail.groupby(['station_id', 'date'])[metrics].sum().reset_index()
    daily.to_csv(out/'top_station_daily_flow.csv', index=False, encoding='utf-8-sig')
    by_type = detail.groupby(['station_id', 'rideable_type'])[metrics].sum().reset_index()
    by_type.to_csv(out/'top_station_vehicle_flow.csv', index=False, encoding='utf-8-sig')

    # 管理投入与车辆调度分别计算：总吞吐量大，不一定存在大的净缺车量。
    peaks = hourly.loc[hourly.day_type.eq('all')].sort_values(
        ['total_activity', 'hour'], ascending=[False, True]).drop_duplicates('station_id')
    top = top.merge(peaks[['station_id', 'hour', 'total_activity']].rename(
        columns={'hour':'peak_activity_hour', 'total_activity':'peak_hour_activity'}), on='station_id')
    top.to_csv(out/'top_station_activity.csv', index=False, encoding='utf-8-sig')

    rows = []
    for (station_id, day_type), group in profile.groupby(['station_id', 'day_type']):
        for low, high, label in WINDOWS:
            window = group.loc[group.hour.ge(low) & group.hour.lt(high)]
            # 先按车型累计窗口净流出，再按正负方向拆分，不能把相反方向相加成一个比例。
            net = window.groupby('rideable_type').net_outflow.sum().reindex(TYPES, fill_value=0)
            days = int(group.n_days.iloc[0])
            need = net.clip(lower=0)
            excess = (-net).clip(lower=0)
            row = {'station_id':station_id, 'day_type':day_type, 'window':label,
                   'n_days':days, 'electric_net':int(net[TYPES[0]]),
                   'classic_net':int(net[TYPES[1]]), 'net_outflow':int(net.sum()),
                   'activity':int(window.total_activity.sum()),
                   'electric_net_per_day':float(net[TYPES[0]]/days),
                   'classic_net_per_day':float(net[TYPES[1]]/days),
                   'replenish_pressure_per_day':float(need.sum()/days),
                   'recover_pressure_per_day':float(excess.sum()/days),
                   'replenish_electric_share':float(need.iloc[0]/need.sum()) if need.sum() else None,
                   'recover_electric_share':float(excess.iloc[0]/excess.sum()) if excess.sum() else None}
            rows.append(row)
    dispatch = pd.DataFrame(rows)
    dispatch.to_csv(out/'top_station_dispatch_windows.csv', index=False, encoding='utf-8-sig')
    audit['top15_activity_share'] = float(top.total_activity.sum()/station.total_activity.sum())
    audit['top15_activity_total'] = int(top.total_activity.sum())
    audit['total_known_stations'] = len(station)
    (out/'station_analysis_summary.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    # 与主程序保持一致，图表直接放在统计结果所在目录。
    draw_station_charts(top, hourly, by_type, out)
    return station


def _font(size):
    for path in [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf',
                 '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _text(draw, xy, value, size=24, fill='#243447', anchor=None):
    draw.text(xy, str(value), font=_font(size), fill=fill, anchor=anchor)


def draw_station_charts(top, hourly, by_type, fig):
    """使用固定中文图例和精确数值标签，图片与 CSV 采用相同站点顺序。"""
    fig.mkdir(exist_ok=True)
    im = Image.new('RGB', (1800, 1160), 'white'); d = ImageDraw.Draw(im)
    _text(d, (45, 20), '高活动站点的流入与流出总量', 40)
    _text(d, (45, 84), '2024年1月 · 已知站点前15名 · 活动量 = 流出 + 流入（端点事件次数）', 26)
    left, right, y0, step = 850, 1650, 170, 58
    mx = top.total_activity.max()
    for row in top.itertuples():
        y = y0+(row.rank-1)*step
        display = row.station_name if len(row.station_name) < 47 else row.station_name.split(' / ')[0]+' …'
        label = f'{row.rank:02d}  {display}'
        size = 32
        while d.textlength(label, font=_font(size)) > left-65:
            size -= 1
        _text(d, (35, y+3), label, size)
        x = left+row.total_activity/mx*(right-left)
        d.rectangle((left, y, x, y+33), fill='#2563eb')
        _text(d, (x+14, y+1), f'{row.total_activity:,}', 32)
    _text(d, (45, 1080), '用于比较巡查与秩序维护工作量；同站出发并返回计两次端点事件，不等于独立骑行数或所需人数。', 25)
    im.save(fig/'03_top_stations_flow.png', dpi=(220,220))

    # 以0为中心的发散色阶，格内为全月同小时的净流出整数，避免只给颜色不给数据。
    im = Image.new('RGB', (1850, 1190), 'white'); d = ImageDraw.Draw(im)
    _text(d, (35, 20), '高活动站点净流出随小时的分布', 40)
    _text(d, (35, 84), '2024年1月同小时累计 · 净流出 = 流出 − 流入（次） · 蓝色为正，橙色为负', 27)
    matrix = hourly.loc[hourly.day_type.eq('all')].pivot(index='station_id', columns='hour', values='net_outflow').reindex(top.station_id)
    bound = max(abs(matrix.to_numpy()).max(), 1)
    left, topy, cw, ch = 270, 180, 64, 56
    for j in range(24):
        _text(d, (left+j*cw+cw/2, topy-30), j, 25, anchor='mm')
    for i, row in enumerate(top.itertuples()):
        _text(d, (30, topy+i*ch+14), f'{row.rank:02d} · {row.station_id}', 27)
        for j in range(24):
            val = int(matrix.iloc[i,j]); weight = abs(val)/bound
            color = (37,99,235) if val > 0 else (232,117,38)
            fill = tuple(round(255*(1-weight)+c*weight) for c in color)
            x,y = left+j*cw,topy+i*ch
            d.rectangle((x,y,x+cw-2,y+ch-2), fill=fill)
            _text(d, (x+cw/2,y+ch/2), f'{val:+d}' if val else '0', 23,
                  fill='white' if weight>.65 else '#18212f', anchor='mm')
    _text(d, (35, 1052), f'颜色范围：−{bound} 至 +{bound}；站点序号与图3相同。正值提示补车压力，负值提示回收压力。', 26)
    _text(d, (35, 1102), '分工作日/周末的小时日均值，以及各日期的实际计数，见配套 CSV；累计值不能直接当作单日调度量。', 25)
    im.save(fig/'07_station_hourly_netflow.png', dpi=(220,220))

    # 报告正文将24小时拆成两幅12小时子图，保证打印时的格内数值可读。
    for low, suffix in [(0,'07a_station_hourly_00_11.png'), (12,'07b_station_hourly_12_23.png')]:
        sub = Image.new('RGB', (1450, 1170), 'white'); pen = ImageDraw.Draw(sub)
        _text(pen,(30,22),f'高活动站点净流出  {low:02d}—{low+11:02d}时',40)
        _text(pen,(30,82),'月累计次数 · 蓝色为正（补车压力），橙色为负（回收压力）',29)
        sx,sy,sw,sh=265,180,95,56
        for j,hour in enumerate(range(low,low+12)):
            _text(pen,(sx+j*sw+sw/2,sy-32),hour,30,anchor='mm')
        for i,row in enumerate(top.itertuples()):
            _text(pen,(25,sy+i*sh+13),f'{row.rank:02d} · {row.station_id}',30)
            for j,hour in enumerate(range(low,low+12)):
                val=int(matrix.iloc[i,hour]); weight=abs(val)/bound
                color=(37,99,235) if val>0 else (232,117,38)
                fill=tuple(round(255*(1-weight)+c*weight) for c in color)
                x,y=sx+j*sw,sy+i*sh
                pen.rectangle((x,y,x+sw-2,y+sh-2),fill=fill)
                _text(pen,(x+sw/2,y+sh/2),f'{val:+d}' if val else '0',30,
                      fill='white' if weight>.65 else '#18212f',anchor='mm')
        _text(pen,(30,1050),f'净流出 = 流出 − 流入；两幅子图统一色阶范围：−{bound} 至 +{bound}。',29)
        _text(pen,(30,1102),'站点序号与图3相同；月累计次数不能直接当作某一天的调度量。',29)
        sub.save(fig/suffix,dpi=(220,220))

    im = Image.new('RGB', (1700, 1240), 'white'); d = ImageDraw.Draw(im)
    _text(d, (35,20), '高活动站点按车型比较净流出', 40)
    _text(d, (35,82), '2024年1月累计 · 向右为净流出（补车压力），向左为净流入（回收压力）', 25)
    colors = {'electric_bike':'#2563eb', 'classic_bike':'#f97316'}
    for x, typ, name in [(40,TYPES[0],'电动车 electric_bike'), (650,TYPES[1],'普通自行车 classic_bike')]:
        d.rectangle((x,135,x+32,157), fill=colors[typ]); _text(d,(x+46,128),name,27)
    wide = by_type.pivot(index='station_id', columns='rideable_type', values='net_outflow').reindex(top.station_id)
    limit = int(np.ceil(max(abs(wide.to_numpy()).max(),1)/50)*50)
    left, right, zero, topy, step = 340,1580,960,238,57
    for value in [-limit, -limit/2, 0, limit/2, limit]:
        x=zero+value/limit*(right-left)/2
        d.line((x,topy-15,x,1100),fill='#d5dce5',width=2)
        _text(d,(x,topy-46),f'{value:.0f}',23,anchor='mm')
    for i,row in enumerate(top.itertuples()):
        y=topy+i*step
        _text(d,(35,y+8),f'{row.rank:02d} · {row.station_id}',30)
        for j,typ in enumerate(TYPES):
            val=int(wide.loc[row.station_id,typ]); xx=zero+val/limit*(right-left)/2
            yy=y+j*23
            d.rectangle((min(xx,zero),yy,max(xx,zero),yy+18),fill=colors[typ])
            _text(d,(xx+8 if val>=0 else xx-8, yy+9),f'{val:+d}',28,anchor='lm' if val>=0 else 'rm')
    _text(d,(35,1142),'两种车型可能方向相反；补车比例只在正净流出车型间计算，回收比例只在负净流出车型间计算。',25)
    _text(d,(35,1190),'具体出车时段与车型比例请使用配套的分工作日/周末、分时间窗口数据。',25)
    im.save(fig/'08_station_vehicle_netflow.png', dpi=(220,220))
