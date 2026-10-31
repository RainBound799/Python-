"""保留现有报告样式，补充会员车型偏好、站点分时和分车型分析。

先运行 analysis.py，再运行此脚本；所有新增表格数值直接读取分析结果。
"""
from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'output'
FIG = OUT/'figures'


def main():
    doc = Document(ROOT/'documents'/'base_report.docx')
    base = list(doc.paragraphs)
    top = pd.read_csv(OUT/'top_station_activity.csv', dtype={'station_id':str})
    hourly = pd.read_csv(OUT/'top_station_hourly_flow.csv', dtype={'station_id':str})
    windows = pd.read_csv(OUT/'top_station_dispatch_windows.csv', dtype={'station_id':str})
    summary = json.loads((OUT/'station_analysis_summary.json').read_text(encoding='utf-8'))
    preference = pd.read_csv(OUT/'user_vehicle_preference.csv')

    def replace(index, text):
        base[index].text = text

    # 更新正文引用，并明确事件口径：出发和到达分别使用真实发生时间。
    replace(18, '起点站点缺失 37,220 条，终点站点缺失 39,741 条；终点经纬度缺失 203 条。'
            '时间分布与模型保留具有有效时间的记录。站点分析只统计已知编号的端点，一端缺失时另一端仍可使用；'
            'UNKNOWN 不参与热点排名。同一编号采用最常见名称，防止名称变体重复计数。')
    replace(21, '站点活动量 = departures + arrivals；净流出 = departures − arrivals。正净流出表示补车压力，'
            '负净流出表示回收压力。实际库存变化的骑行部分与净流出符号相反。')
    replace(30, '4.2 高活动站点与管理投入')
    replace(31, f'按已知站点的流入与流出之和选取前15名。图3显示 Union Station 活动量为5,925次，'
            f'其次为 New Hampshire Ave & T St NW 的5,047次。前15站合计{summary["top15_activity_total"]:,}次，'
            f'占全部已知端点活动的{summary["top15_activity_share"]:.2%}。该指标衡量停车秩序维护、巡查和引导的相对工作量；'
            '同一骑行若两端均在同站，会贡献两次端点事件，因此活动量不是独立骑行次数。')
    replace(33, '图 3　高活动站点的流入与流出总量')
    replace(37, '有效记录中会员占74.1%，非会员占25.9%；电动车占51.0%，普通自行车占49.0%。'
            '图5明确标注蓝色为非会员 casual、橙色为会员 member。全网车型使用比例只描述骑行构成，'
            '具体站点应按时段、按车型的净流出计算补车或回收比例，不能直接沿用全网的51∶49。')
    replace(39, '图 5　不同会员类型的小时需求　蓝色为非会员　橙色为会员')
    replace(46, '图 9　时间顺序测试集上的小时需求预测')
    replace(48, '全月17时骑行量最高，但单站调度方向并不一致。Union Station 工作日早间净流入、晚间净流出，'
            'New Hampshire Ave & T St NW 则主要呈现相反方向。活动量反映管理工作量，净流出反映车辆流动压力；'
            '按车型细分后，月度接近平衡的站点也可能需要定时交换车型。')
    replace(51, '管理投入：对前15站的专用巡查资源，可先按各站活动量占前15站总量的比例分配，再叠加高峰小时、'
            '站点容量及现场违停情况。Union Station 权重约11.0%，New Hampshire Ave & T St NW 约9.4%；'
            '这些是前15站之间的相对工作量权重，不代表全市警力占比或应配置的绝对人数。')
    replace(52, '补车与回收：工作日7时前优先检查 New Hampshire Ave & T St NW、15th & P St NW、14th & V St NW 的库存；'
            'Union Station 在7—10时关注回收/车位压力，16时前转为补车检查。现场库存充足时不必机械搬运。')
    replace(53, '车型配置：Union Station 工作日16—20时的补车压力中，电动车占13.6%、普通自行车占86.4%；'
            '7—10时回收压力的电动车占17.4%。不同时段分别计算；两种车型方向相反时应同时列出补车和回收任务。')
    replace(54, '执行规则：以分时净流出日均值作为调度优先级参考，结合当前库存、容量、电量和路程设定执行数量。'
            '月累计净流出不能直接作为某一天的调度量；还应查看逐日记录及窗口内部的小时变化，避免平均值掩盖突发压力。')
    replace(57, 'A负责统筹与数据清洗复核，B负责时空分析与图表复核，C负责模型、调度建议和报告复核。'
            '历史提交中的A、B、C为模块署名标记；个人实际承担情况应由成员核实，不能仅凭署名替代独立贡献证明。')
    replace(60, '将完整代码包解压，并将原始CSV放到analysis.py所在文件夹。运行 analysis.py 生成分析结果，运行 update_report.py '
            '更新报告。统计表、JSON摘要和本报告保存到代码旁的output子文件夹，PNG图表保存到output/figures。其中包含9类图表（小时热力图另有两张拆分子图），以及会员车型组内占比、站点日期、小时、日类型、车型和调度窗口统计表。'
            '原始CSV仅保留在本地，不随代码提交；配套压缩包另附本次统计结果。')
    replace(63, 'Python 3.12；分析依赖 pandas、numpy、Pillow，报告更新另需 python-docx。'
            '输入文件名为题5_共享单车骑行_202401.csv。运行 python -m unittest -v test_station_analysis.py test_membership_analysis.py '
            '可检查跨小时、跨月、单端缺失、零计数及会员组内占比分母等情形。')

    # 图片段落替换后，重新绑定图片说明，保持Word中的图像可访问性。
    def picture(p, filename, alt, width=6.25):
        p.clear()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(2)
        image = p.add_run().add_picture(str(FIG/filename), width=Inches(width))
        image._inline.docPr.set('descr', alt)
        image._inline.docPr.set('title', alt)
    picture(base[32], '03_top_stations_flow.png', base[33].text)
    picture(base[38], '05_membership_hourly.png', base[39].text)
    # 同步修复原折线图标题与图例距离，使用重新生成的同源结果。
    picture(base[26], '01_hourly_demand.png', base[27].text)
    picture(base[34], '04_hourly_net_flow.png', base[35].text)
    picture(base[45], '06_model_prediction.png', base[46].text)

    def para(anchor, text, heading=None):
        return anchor.insert_paragraph_before(text, style=heading or 'Normal')

    def figure(anchor, filename, caption):
        p = para(anchor, '')
        picture(p, filename, caption)
        cap = para(anchor, caption)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.runs[0].font.size = Pt(9)

    def table(anchor, headers, rows, widths):
        t = doc.add_table(rows=1, cols=len(headers))
        t.autofit = False
        for col, width in zip(t.columns, widths):
            col.width = Inches(width)
        for i, h in enumerate(headers):
            t.rows[0].cells[i].text = h
        for values in rows:
            for cell, value in zip(t.add_row().cells, values):
                cell.text = str(value)
        t.style = 'Table Grid'
        borders = OxmlElement('w:tblBorders')
        for edge in ['top','left','bottom','right','insideH','insideV']:
            e = OxmlElement('w:'+edge)
            for key, val in [('val','single'),('sz','4'),('color','D9D9D9')]:
                e.set(qn('w:'+key),val)
            borders.append(e)
        t._tbl.tblPr.append(borders)
        for r, row in enumerate(t.rows):
            trpr = row._tr.get_or_add_trPr()
            trpr.append(OxmlElement('w:cantSplit'))
            if r == 0:
                trpr.append(OxmlElement('w:tblHeader'))
            for i, cell in enumerate(row.cells):
                cell.width = Inches(widths[i])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(3)
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.line_spacing = 1.12
                    for run in p.runs:
                        run.font.size = Pt(9)
                        if r == 0:
                            run.bold = True
                            run.font.color.rgb = RGBColor(255,255,255)
                if r == 0:
                    shd = OxmlElement('w:shd'); shd.set(qn('w:fill'),'1F4E78')
                    cell._tc.get_or_add_tcPr().append(shd)
        anchor._p.addprevious(t._tbl)
        return t

    para(base[34], '表 1　前15个高活动站点及管理投入参考')
    rows=[]
    for r in top.itertuples():
        rows.append([f'{r.rank:02d}\n{r.station_id}',r.station_name,f'{r.total_activity:,}',
                     f'{r.activity_per_day:.1f}',f'{r.activity_share_top15:.1%}',f'{r.peak_activity_hour:02d}时'])
    table(base[34], ['序号\n编号','站点名称','总活动量\n次/月','日均\n次/日','前15站\n内权重','活动量\n峰值小时'],
          rows,[.55,2.65,.8,.65,.75,.75])
    para(base[34], '管理权重 = 本站活动量 ÷ 前15站活动量总和。若已明确分给这15站的总巡查工时为H，'
         '初始工时可按H×权重安排；应设置最低巡查覆盖，再用各时段活动量修正，不根据该表直接推断人数。')
    para(base[34], '站点统计限定端点时间在2024年1月1日00:00至2月1日00:00之前；17条已知站点的次月到达端点被排除。'
         '数据文件以1月出发记录为基础，不能覆盖12月出发、1月到达的跨月骑行，月初存在边界限制。'
         '图4仍为有效骑行样本的全网按时钟小时流量，用于总体描述；具体调度采用下文按站点的事件统计。')

    anchor = base[40]
    para(anchor, '4.4 不同会员类型的车型偏好', 'Heading 2')
    para(anchor, '使用与前文相同的235,674条有效骑行，按会员类型与车型交叉统计。'
         '组内车型占比 = 该会员类型使用该车型的骑行次数 ÷ 该会员类型全部骑行次数。'
         '每个会员群体内部的两种车型占比合计100%，避免会员总体骑行量较多造成误判。'
         '这里的“偏好”指已完成骑行中观察到的车型使用倾向，统计单位是骑行次数，而非独立用户人数。')
    figure(anchor, '09_membership_vehicle_preference.png', '图 6　不同会员类型的车型组内占比与骑行次数')
    para(anchor, '表 2　会员类型与车型交叉统计')
    rows=[]
    for member, label in [('casual', '非会员 casual'), ('member', '会员 member')]:
        group = preference.loc[preference.member_casual.eq(member)].set_index('rideable_type')
        e, c = group.loc['electric_bike'], group.loc['classic_bike']
        rows.append([label, f'{int(e.rides):,}', f'{e.within_membership_share:.2%}',
                     f'{int(c.rides):,}', f'{c.within_membership_share:.2%}', f'{int(e.membership_total):,}'])
    table(anchor, ['会员类型','电动车\n次数','电动车\n组内占比','普通车\n次数','普通车\n组内占比','组内总次数'],
          rows, [1.25, 1.0, 1.0, 1.0, 1.0, 1.0])
    shares = preference.loc[preference.rideable_type.eq('electric_bike')].set_index('member_casual').within_membership_share
    gap = (shares['casual'] - shares['member']) * 100
    para(anchor, f'非会员电动车占比为{shares["casual"]:.2%}，会员为{shares["member"]:.2%}，'
         f'非会员高出{gap:.2f}个百分点。会员普通自行车占比为{1-shares["member"]:.2%}，两种车型接近，普通车略多。'
         '因此可描述为非会员更常使用电动车，而会员车型使用较均衡。虽然会员电动车次数多于非会员，'
         '这是两个群体规模不同的结果，不能用绝对次数替代组内占比来比较使用倾向。')
    para(anchor, '该结果可作为了解用户构成和车型需求的参考。数据缺少独立用户标识、价格、现场可用车辆和电量，'
         '同一用户可能贡献多次骑行，因此不能据此认定个人主观偏好或会员身份的因果影响。'
         '站点实际补收车型比例仍应结合下文的分站点、分时段净流出和实时库存决定。'
         '精确次数、组内分母及未四舍五入占比保存在user_vehicle_preference.csv。')

    para(anchor, '4.5 高活动站点分时净流出与补收车时段', 'Heading 2')
    para(anchor, '对同一批前15站分别统计实际出发小时与到达小时，图7给出每个小时的月累计净流出整数。'
         '蓝色表示净流出为正、车辆被骑走更多；橙色表示净流出为负、车辆流入更多。'
         '例如Union Station在7时净流出为−129次，在18时为+104次；New Hampshire Ave & T St NW在7时为+184次，'
         '17时为−143次，显示不同站点的调度方向相反。')
    figure(anchor, '07a_station_hourly_00_11.png', '图 7a　高活动站点0至11时净流出　单元格为月累计次数')
    figure(anchor, '07b_station_hourly_12_23.png', '图 7b　高活动站点12至23时净流出　单元格为月累计次数')
    para(anchor, '进一步按日类型划分：周一至周五计23天，周末计8天；这里的“工作日”为日历分类，未另做节假日调整。'
         '零骑行日期与小时同样进入分母。下表列出各站净流出日均值最大与最小的小时，正值提示在该小时前检查补车，'
         '负值提示该小时内关注车位并视库存回收；每个小时均指[该时,下一时)。')
    para(anchor, '表 3　前15站工作日与周末的小时补收车压力')
    def extremes(station_id, kind):
        g=hourly.loc[hourly.station_id.eq(station_id)&hourly.day_type.eq(kind)].sort_values('hour')
        hi=g.loc[g.net_outflow_per_day.idxmax()]; lo=g.loc[g.net_outflow_per_day.idxmin()]
        return f'{int(hi.hour):02d}时 {hi.net_outflow_per_day:+.2f}',f'{int(lo.hour):02d}时 {lo.net_outflow_per_day:+.2f}'
    rows=[]
    for r in top.itertuples():
        rows.append([f'{r.rank:02d} / {r.station_id}',*extremes(r.station_id,'weekday'),*extremes(r.station_id,'weekend')])
    table(anchor,['序号 / 编号','工作日\n最大净流出','工作日\n最小净流出','周末\n最大净流出','周末\n最小净流出'],
          rows,[1.05,1.3,1.3,1.3,1.2])
    para(anchor, '表3单位为次/日（对应所示小时）；月累计量、日均值和逐日实际量分别保存在配套CSV中。'
         '例如日均+5表示历史上该时段每天平均净骑走5次，不能据此保证每天补5辆即可满足需求。'
         '骑行记录不含调度搬运、站点容量、初始库存和未成功借车需求，应结合实时库存与逐日波动判断实际数量。')

    para(anchor, '4.6 分车型净流出与调度比例', 'Heading 2')
    para(anchor, '保持相同站点和时间口径，将端点事件分别归入电动车 electric_bike 与普通自行车 classic_bike。'
         '图8用于比较月度累计方向；例如Adams Mill & Columbia Rd NW电动车净流出+21次、普通自行车+286次，'
         '普通车的累计补充压力更明显。M St & Delaware Ave NE电动车+23次、普通车−10次，应区分电动车补充和普通车回收。')
    figure(anchor, '08_station_vehicle_netflow.png', '图 8　高活动站点的电动车与普通自行车净流出对比')
    para(anchor, '单日调度使用分日类型、分窗口的净流出。设某车型的窗口日均净流出为N，补车压力取max(N,0)，'
         '回收压力取max(−N,0)。电动车补车占比为电动车正净流出除以两车型正净流出之和；回收占比按负净流出的绝对值另算。'
         '分母为零时不定义比例。该比例是历史窗口净变化的参考，不是已验证的最优调度比例；窗口内有反转时还须查看逐小时数据。')
    para(anchor, '表 4　前四站工作日早晚窗口的车型调度参考')
    rows=[]
    for r in top.head(4).itertuples():
        for label in ['07–10','16–20']:
            w=windows.loc[windows.station_id.eq(r.station_id)&windows.day_type.eq('weekday')&windows.window.eq(label)].iloc[0]
            need=w.replenish_pressure_per_day; recover=w.recover_pressure_per_day
            if need>0 and recover==0:
                action=f'补车压力 {need:.2f}'
                share=f'{w.replenish_electric_share:.1%} / {1-w.replenish_electric_share:.1%}'
            elif recover>0 and need==0:
                action=f'回收压力 {recover:.2f}'
                share=f'{w.recover_electric_share:.1%} / {1-w.recover_electric_share:.1%}'
            else:
                action='分车型分别处理'; share='详见配套CSV'
            rows.append([f'{r.rank:02d} / {r.station_id}',label,
                         f'{w.electric_net_per_day:+.2f}',f'{w.classic_net_per_day:+.2f}',action,share])
    table(anchor,['序号 / 编号','时段','电动车\n净流出','普通车\n净流出','合计方向\n次/日','方向内比例\n电动车 / 普通车'],
          rows,[.95,.65,.8,.8,1.25,1.7])
    para(anchor, '表4以23个工作日为分母，07—10时包含07、08、09三个小时，16—20时包含16、17、18、19四个小时。'
         'Union Station早间回收压力日均11.74次、晚间补车压力日均10.22次，电动车占比分别为17.4%和13.6%。'
         '这些数值刻画历史净变化；执行前应检查剩余车位、可用车辆和电动车电量。全15站及周末的5个时间窗口明细均已导出。')

    anchor = base[62]
    para(anchor, '附录 C 新增统计数据说明', 'Heading 2')
    table(anchor,['数据文件','内容与单位'],[
        ['top_station_activity.csv','前15站名单、流入+流出次数、日均活动、管理权重和活动峰值小时'],
        ['top_station_hourly_flow.csv','全月/工作日/周末 × 站点 × 小时：流出、流入、净流出及日均值'],
        ['top_station_daily_flow.csv','站点逐日期的实际流量，包含零骑行日期'],
        ['top_station_vehicle_flow.csv','站点 × 车型的月累计流量，支持核对图8'],
        ['top_station_hourly_vehicle.csv','日类型 × 站点 × 小时 × 车型：累计次数与日均值'],
        ['top_station_date_hour_vehicle.csv','15站 × 31天 × 24小时 × 2车型，共22,320行精确计数'],
        ['top_station_dispatch_windows.csv','00—07、07—10、10—16、16—20、20—24时：车型净流出和分别补/收的比例'],
        ['station_analysis_summary.json','统计时段、已知端点数量、跨月排除数与各类天数'],
        ['user_vehicle_preference.csv','会员类型 × 车型的骑行次数、会员组内总次数及组内车型占比']
    ],[2.65,3.5])
    para(anchor, 'CSV采用UTF-8 BOM编码。departures为流出次数，arrivals为流入次数，total_activity为二者之和，'
         'net_outflow为二者之差；后缀_per_day表示除以对应日类型天数后的日均值。'
         'electric指电动车，classic指普通自行车；比例列为0—1的小数，无需该方向调度时留空。')
    replace(62, '附录 D 复现环境')

    # 图像不越过页面正文宽度，图注与图保持相邻，表格跨页重复表头。
    for p in doc.paragraphs:
        for inline in p._p.xpath('.//wp:inline'):
            extent=inline.find(qn('wp:extent'))
            if extent is not None and int(extent.get('cx'))>int(Inches(6.3)):
                ratio=int(Inches(6.3))/int(extent.get('cx'))
                for e in inline.xpath('.//a:xfrm/a:ext'):
                    e.set('cx',str(int(int(e.get('cx'))*ratio)))
                    e.set('cy',str(int(int(e.get('cy'))*ratio)))
                extent.set('cx',str(int(int(extent.get('cx'))*ratio)))
                extent.set('cy',str(int(int(extent.get('cy'))*ratio)))
    output=OUT/'项目报告_题目五_修订版.docx'
    doc.save(output)
    print(output)


if __name__ == '__main__':
    main()
