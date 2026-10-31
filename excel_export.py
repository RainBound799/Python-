"""将统计CSV与对应PNG汇总到Excel，同页对照查看，支持普通Python环境复现。"""
from pathlib import Path
import math
import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# 明确指定数据和图表的对应关系，避免仅按文件序号误配或包含过期文件。
SHEETS = [
    ('小时需求', 'hourly_demand.csv', '01_hourly_demand.png', '按出发小时统计的全月骑行次数。'),
    ('星期小时分布', 'weekday_hour_heatmap.csv', '02_weekday_hour_heatmap.png', '月累计次数，未按各星期出现天数归一化。'),
    ('高活动站点', 'top_station_activity.csv', '03_top_stations_flow.png', '前15站活动量＝流出＋流入，单位为端点事件次数。'),
    ('全网小时净流出', 'hourly_net_flow.csv', '04_hourly_net_flow.png', '流出按开始小时、流入按结束小时汇总，净流出＝流出－流入。'),
    ('会员小时需求', 'membership_hourly.csv', '05_membership_hourly.png', '蓝色为非会员casual，橙色为会员member，单位为骑行次数。'),
    ('会员车型偏好', 'user_vehicle_preference.csv', '09_membership_vehicle_preference.png', '占比分母为该会员群体的全部骑行次数，非独立用户人数。'),
    ('站点分时净流出', 'top_station_hourly_flow.csv', '07_station_hourly_netflow.png', '图为all口径的月累计净流出。表另含工作日、周末及日均值，不能混读。'),
    ('站点车型净流出', 'top_station_vehicle_flow.csv', '08_station_vehicle_netflow.png', '图表均为同一批前15站的分车型月累计净流出，正值提示补车压力。'),
    ('模型预测明细', 'model_predictions.csv', '06_model_prediction.png', '按时间顺序留出的测试集。图表单位为每小时骑行次数。'),
    ('模型评价', 'model_metrics.csv', None, 'MAE、RMSE单位为次，越低越好；R²越高越好，不是准确率。'),
    ('清洗统计', 'cleaning_summary.csv', None, '时长单位为分钟，保留率为有效记录数占原始记录数的比例。'),
    ('全站点流量', 'station_supply_demand.csv', None, '已知站点端点统计，活动量＝流出＋流入，净流出＝流出－流入。'),
    ('站点逐日流量', 'top_station_daily_flow.csv', None, '按实际事件日期统计，包含零骑行日期。'),
    ('站点分时车型', 'top_station_hourly_vehicle.csv', None, '按日类型、站点、小时、车型统计；日均值使用对应日类型天数。'),
    ('站点日期小时车型', 'top_station_date_hour_vehicle.csv', None, '15站×31天×24小时×2车型，完整导出22,320行，不截取。'),
    ('站点调度窗口', 'top_station_dispatch_windows.csv', None, '先按时间窗口计算各车型净流出，再分别计算补车与回收比例；无压力时比例留空。'),
    ('会员车型次数', 'user_vehicle_profile.csv', None, '会员类型与车型的原始交叉次数；占比及对应图见“会员车型偏好”。'),
]

LABELS = {
    'hour':'小时', 'rides':'骑行次数', 'weekday':'星期', 'casual':'非会员次数', 'member':'会员次数',
    'rank':'排名', 'station_id':'站点编号', 'station_name':'站点名称', 'departures':'流出次数',
    'arrivals':'流入次数', 'total_activity':'总活动量', 'net_outflow':'净流出', 'day_type':'日类型',
    'n_days':'日类型天数', 'date':'日期', 'rideable_type':'车型', 'member_casual':'会员类型',
    'membership_total':'会员组内总次数', 'within_membership_share':'车型组内占比',
    'activity_per_day':'日均活动量', 'activity_share_top15':'前15站内活动占比',
    'activity_share_all_known':'全部已知端点中活动占比', 'peak_hour_activity':'峰值小时活动量',
    'Unnamed: 0':'小时',
    'peak_activity_hour':'活动量峰值小时', 'imbalance_index':'失衡指数',
    'departures_per_day':'日均流出', 'arrivals_per_day':'日均流入',
    'total_activity_per_day':'日均活动量', 'net_outflow_per_day':'日均净流出',
    'started_at':'出发时间', 'actual':'实际骑行量', 'seasonal_mean':'时段星期均值预测',
    'ridge':'岭回归预测', 'model':'模型', 'MAE':'MAE（次）', 'RMSE':'RMSE（次）', 'R2':'R²',
    'window':'时间窗口', 'electric_net':'电动车净流出', 'classic_net':'普通车净流出',
    'activity':'窗口活动量', 'electric_net_per_day':'电动车日均净流出',
    'classic_net_per_day':'普通车日均净流出', 'replenish_pressure_per_day':'日均补车压力',
    'recover_pressure_per_day':'日均回收压力', 'replenish_electric_share':'补车中电动车占比',
    'recover_electric_share':'回收中电动车占比', 'raw_rows':'原始记录数',
    'duplicate_ride_ids':'重复骑行编号数', 'valid_rows':'有效记录数', 'removed_rows':'剔除记录数',
    'valid_rate':'有效记录保留率', 'duration_min_median':'时长中位数（分钟）',
    'duration_min_mean':'平均时长（分钟）', 'duration_min_p95':'时长95%分位数（分钟）',
    'start_station_missing_raw':'原始起点缺失数', 'end_station_missing_raw':'原始终点缺失数',
    'end_coordinate_missing_raw':'原始终点坐标缺失数',
}
NAVY = '243F54'


def export_excel(out):
    """输出一个含全部统计表和9幅对应图表的工作簿，PNG为静态图片。"""
    out = Path(out)
    book = Workbook()
    index = book.active
    index.title = '结果目录'
    index.sheet_view.showGridLines = False
    index.column_dimensions['A'].width = 26
    index.column_dimensions['B'].width = 45
    index.column_dimensions['C'].width = 14
    index.column_dimensions['D'].width = 18
    index['A2'] = '共享单车分析结果'
    index['A2'].font = Font(name='微软雅黑', size=16, bold=True, color=NAVY)
    notes = [
        '2024年1月。点击工作表名称查看表格与对应图表。',
        '图表为本次运行的静态PNG，修改Excel单元格不会同步改变图片。更新结果请重新运行analysis.py。',
        '日类型：all为全月31天，weekday为周一至周五23天，weekend为周末8天。未调整节假日。',
        '车型：electric_bike为电动车，classic_bike为普通自行车。member为会员，casual为非会员。',
        '正净流出提示补车压力，负值提示回收压力；调度数量需结合实时库存与车位。',
    ]
    for row, note in enumerate(notes, 4):
        index.cell(row, 1, note).font = Font(name='微软雅黑', size=11, color='526576')
        index.row_dimensions[row].height = 23
    index.append([])
    for col, value in enumerate(['统计主题', '来源CSV', '数据行数', '对应图表'], 1):
        index.cell(10, col, value)

    body_font = Font(name='微软雅黑', size=11, color='243447')
    for sheet_number, (title, csv_name, figure, note) in enumerate(SHEETS, 1):
        # 编号保持字符串，避免编号被转换成小数或丢掉前导零。
        frame = pd.read_csv(out/csv_name, encoding='utf-8-sig', dtype={'station_id':'string'})
        sheet = book.create_sheet(title)
        sheet.sheet_view.showGridLines = False
        sheet.sheet_view.zoomScale = 85
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = 'landscape'
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0
        sheet['A2'] = title
        sheet['A2'].font = Font(name='微软雅黑', size=16, bold=True, color=NAVY)
        sheet['A3'] = note
        sheet['A3'].font = Font(name='微软雅黑', size=11, color='526576')
        sheet['A4'] = f'来源：{csv_name}。表头批注保留原始字段名。'
        sheet['A4'].font = Font(name='微软雅黑', size=10, color='526576')
        sheet['A5'] = '返回结果目录'
        sheet['A5'].hyperlink = "#'结果目录'!A1"
        sheet['A5'].style = 'Hyperlink'
        header = 7
        if figure:
            picture = Image(out/'figures'/figure)
            ratio = min(1, 1100/picture.width)
            picture.width, picture.height = picture.width*ratio, picture.height*ratio
            sheet.add_image(picture, 'A7')
            # 为图片保留实际像素所需的空行，避免覆盖任何表格数据。
            rows = math.ceil(picture.height/24)
            for row in range(7, 7+rows):
                sheet.row_dimensions[row].height = 18
            header = 7+rows+2
            sheet['D5'] = '跳转到数据表'
            sheet['D5'].hyperlink = f"#'{title}'!A{header}"
            sheet['D5'].style = 'Hyperlink'
        else:
            sheet.freeze_panes = 'B8'
        for col, field in enumerate(frame.columns, 1):
            label = LABELS.get(field, f'{field}时' if field.isdigit() else field)
            cell = sheet.cell(header, col, label)
            cell.comment = Comment(field, '字段说明')
            cell.font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=NAVY)
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            width = 46 if field == 'station_name' else 23 if field == 'started_at' else 20
            if field.isdigit():
                width = 10
            sheet.column_dimensions[get_column_letter(col)].width = width
        sheet.row_dimensions[header].height = 32
        for row_num, values in enumerate(frame.itertuples(index=False, name=None), header+1):
            for col, (field, value) in enumerate(zip(frame.columns, values), 1):
                if pd.isna(value):
                    value = None  # 无定义比例保持空白，不伪装成0%。
                elif field in ['date', 'started_at']:
                    value = pd.Timestamp(value).to_pydatetime()
                cell = sheet.cell(row_num, col, value)
                cell.font = body_font
                cell.alignment = Alignment(vertical='center')
                if isinstance(value, str):
                    cell.data_type = 's'  # 文本类别原样保留，不当作Excel公式执行。
                if field in ['date', 'started_at']:
                    cell.number_format = 'yyyy-mm-dd hh:mm' if field == 'started_at' else 'yyyy-mm-dd'
                elif 'share' in field or field == 'valid_rate':
                    cell.number_format = '0.00%'
                elif field == 'R2' or field == 'imbalance_index':
                    cell.number_format = '0.000'
                elif field in ['MAE', 'RMSE', 'seasonal_mean', 'ridge'] or 'per_day' in field or field.startswith('duration_'):
                    cell.number_format = '#,##0.00'
                elif isinstance(value, (int, float)):
                    cell.number_format = '#,##0'
            sheet.row_dimensions[row_num].height = 20
        last = header+len(frame)
        sheet.auto_filter.ref = f'A{header}:{get_column_letter(len(frame.columns))}{last}'
        sheet.print_title_rows = f'{header}:{header}'
        row = sheet_number+10
        index.cell(row, 1, title).hyperlink = f"#'{title}'!A1"
        index.cell(row, 1).style = 'Hyperlink'
        index.cell(row, 2, csv_name)
        index.cell(row, 3, len(frame))
        index.cell(row, 4, '已嵌入' if figure else '无对应图表')
        index.row_dimensions[row].height = 23
    for cell in index[10]:
        cell.fill = PatternFill('solid', fgColor=NAVY)
        cell.font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
    target = out/'分析结果汇总.xlsx'
    # 先写临时文件再替换，避免导出中断后留下损坏的正式结果。
    temporary = out/'分析结果汇总.tmp.xlsx'
    try:
        book.save(temporary)
        temporary.replace(target)
    finally:
        book.close()
        temporary.unlink(missing_ok=True)
    return target


if __name__ == '__main__':
    print(export_excel(Path(__file__).resolve().parent/'output'))
