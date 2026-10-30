"""比较不同会员群体的车型使用构成；一次有效骑行计一次，不代表独立用户。"""
import pandas as pd


def membership_preference(df):
    """补齐会员×车型组合，以各会员群体自己的骑行总数计算占比。"""
    data = df[['member_casual', 'rideable_type']].fillna('unknown')
    # 显式保留未知类别，避免缺失值被分组操作悄悄丢弃。
    members = ['casual', 'member']
    vehicles = ['electric_bike', 'classic_bike']
    members += sorted(set(data.member_casual) - set(members))
    vehicles += sorted(set(data.rideable_type) - set(vehicles))
    grid = pd.MultiIndex.from_product([members, vehicles], names=data.columns)
    counts = data.groupby(list(data.columns)).size().reindex(grid, fill_value=0)
    result = counts.rename('rides').reset_index()
    result['membership_total'] = result.groupby('member_casual').rides.transform('sum')
    # 没有骑行记录的群体占比不定义；不把“无样本”写成0%偏好。
    denominator = result.membership_total.where(result.membership_total.ne(0))
    result['within_membership_share'] = result.rides / denominator
    return result


def preference_chart(profile, output, font):
    """用100%堆积条形图比较组内占比，附原始次数和清晰的车型图例。"""
    from PIL import Image, ImageDraw
    ink, muted = '#142D42', '#526576'
    members = profile.member_casual.unique().tolist()
    vehicles = profile.rideable_type.unique().tolist()
    member_names = {'casual': '非会员 casual', 'member': '会员 member', 'unknown': '未知会员类别'}
    vehicle_names = {'electric_bike': '电动车', 'classic_bike': '普通自行车', 'unknown': '未知车型'}
    palette = ['#2766C2', '#E77C35', '#788796', '#43846D']
    # 实际课程数据为两类会员、两类车型；扩展类别时同步扩大画布。
    height = max(700, 330 + 160 * len(members))
    image = Image.new('RGB', (1500, height), 'white')
    draw = ImageDraw.Draw(image)
    draw.text((70, 28), '不同会员类型的车型使用构成', font=font(38), fill=ink)
    draw.text((70, 91), '2024年1月有效骑行 · 每条横柱以该会员群体全部骑行为100%', font=font(25), fill=muted)
    for j, vehicle in enumerate(vehicles):
        x = 360 + j * 330
        draw.rectangle((x, 155, x + 28, 183), fill=palette[j % len(palette)])
        draw.text((x + 42, 151), vehicle_names.get(vehicle, vehicle), font=font(26), fill=ink)
    left, right = 360, 1400
    for i, member in enumerate(members):
        group = profile.loc[profile.member_casual.eq(member)].set_index('rideable_type')
        y = 235 + i * 160
        total = int(group.membership_total.iloc[0])
        draw.text((65, y + 8), member_names.get(member, member), font=font(28), fill=ink)
        draw.text((65, y + 55), f'共 {total:,} 次', font=font(24), fill=muted)
        x = left
        if total == 0:
            draw.text((left, y + 10), '无样本，占比未定义', font=font(26), fill=muted)
        for j, vehicle in enumerate(vehicles):
            row = group.loc[vehicle]
            if total == 0 or row.rides == 0:
                continue
            width = float(row.within_membership_share) * (right - left)
            draw.rectangle((x, y, x + width, y + 95), fill=palette[j % len(palette)])
            label = f'{row.within_membership_share:.2%}\n{int(row.rides):,} 次'
            draw.multiline_text((x + width / 2, y + 47), label, anchor='mm', align='center',
                                spacing=8, font=font(26), fill='white')
            x += width
    baseline = 235 + 160 * len(members)
    for tick in range(5):
        x = left + (right - left) * tick / 4
        draw.text((x, baseline), f'{tick * 25}%', anchor='mt', font=font(22), fill=muted)
    draw.text((70, height - 60), '口径：骑行次数，非独立用户人数；观察到的使用构成还受价格与可用车辆影响。',
              font=font(24), fill=muted)
    image.save(output, dpi=(180, 180))
