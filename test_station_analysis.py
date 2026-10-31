"""检查跨小时、跨月、单端缺失等会影响调度方向的关键场景。"""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from station_analysis import endpoint_events, flow_counts


class EndpointCountingTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({
            'start_station_id':['A', 'UNKNOWN', 'A'],
            'end_station_id':['B', 'B', 'B'],
            'start_station_name':['甲', 'Unknown station', '甲'],
            'end_station_name':['乙', '乙', '乙'],
            'started_at':pd.to_datetime(['2024-01-02 07:55', '2024-01-03 08:10', '2024-01-31 23:50']),
            'ended_at':pd.to_datetime(['2024-01-02 08:05', '2024-01-03 08:20', '2024-02-01 00:10']),
            'rideable_type':['electric_bike', 'classic_bike', 'classic_bike'],
        })

    def test_endpoints_use_actual_time_and_keep_known_half(self):
        events, audit = endpoint_events(self.data)
        arrivals = events.loc[events.direction.eq('arrivals')]
        self.assertEqual(arrivals.hour.tolist(), [8, 8])
        self.assertEqual(len(events), 4)
        self.assertEqual(audit['known_endpoint_events_outside_month'], 1)
        self.assertNotIn('UNKNOWN', events.station_id.tolist())

    def test_zero_hour_and_vehicle_direction(self):
        events, _ = endpoint_events(self.data)
        idx = pd.MultiIndex.from_product([['A','B'], range(24)], names=['station_id','hour'])
        counts = flow_counts(events, ['station_id','hour'], idx).set_index(['station_id','hour'])
        self.assertEqual(len(counts), 48)
        self.assertEqual(counts.loc[('A',7),'net_outflow'], 1)
        self.assertEqual(counts.loc[('B',8),'net_outflow'], -2)
        self.assertEqual(counts.loc[('B',0),'total_activity'], 0)
        by_type = flow_counts(events, ['station_id','rideable_type']).set_index(['station_id','rideable_type'])
        self.assertEqual(by_type.loc[('B','electric_bike'),'net_outflow'], -1)
        self.assertEqual(by_type.loc[('B','classic_bike'),'net_outflow'], -1)


class GeneratedOutputTests(unittest.TestCase):
    """用原始端点独立核对结果，并验证各层级统计可以互相还原。"""
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.out = cls.root
        if not (cls.out/'top_station_activity.csv').exists():
            raise unittest.SkipTest('先运行 analysis.py 生成结果，再核对全量数据')

    def read(self, name):
        return pd.read_csv(self.out/name, dtype={'station_id':str})

    def test_activity_matches_source_endpoints(self):
        raw = pd.read_csv(self.root/'题5_共享单车骑行_202401.csv',
                          dtype={'start_station_id':str,'end_station_id':str})
        begin = pd.to_datetime(raw.started_at, errors='coerce')
        end = pd.to_datetime(raw.ended_at, errors='coerce')
        duration = (end-begin).dt.total_seconds()/60
        valid = raw.ride_id.notna() & duration.between(.5,1440) & ~raw.ride_id.duplicated()
        jan = lambda t: t.ge('2024-01-01') & t.lt('2024-02-01')
        departures = raw.loc[valid & jan(begin),'start_station_id'].value_counts()
        arrivals = raw.loc[valid & jan(end),'end_station_id'].value_counts()
        expected = departures.add(arrivals,fill_value=0)
        top = self.read('top_station_activity.csv')
        self.assertEqual(len(top),15)
        self.assertEqual(top.station_id.nunique(),15)
        for row in top.itertuples():
            self.assertEqual(row.total_activity, expected[row.station_id])
            self.assertEqual(row.departures,departures[row.station_id])
            self.assertEqual(row.arrivals,arrivals[row.station_id])
        self.assertEqual(set(top.station_id),set(expected.nlargest(15).index))
        self.assertAlmostEqual(top.activity_share_top15.sum(),1)

    def test_date_hour_type_rollups_and_day_denominators(self):
        detail = self.read('top_station_date_hour_vehicle.csv')
        top = self.read('top_station_activity.csv').set_index('station_id')
        self.assertEqual(len(detail),15*31*24*2)
        pd.testing.assert_series_equal(
            detail.groupby('station_id').net_outflow.sum().sort_index(),
            top.net_outflow.sort_index(), check_names=False)
        hourly = self.read('top_station_hourly_flow.csv')
        all_hours = hourly.loc[hourly.day_type.eq('all')].set_index(['station_id','hour'])
        split = hourly.loc[~hourly.day_type.eq('all')].groupby(['station_id','hour']).net_outflow.sum()
        pd.testing.assert_series_equal(all_hours.net_outflow.sort_index(),split.sort_index(),check_names=False)
        np.testing.assert_allclose(hourly.net_outflow_per_day*hourly.n_days,hourly.net_outflow,atol=1e-10)
        self.assertEqual(hourly.groupby('day_type').n_days.first().to_dict(),{'all':31,'weekday':23,'weekend':8})

    def test_replenishment_and_recovery_never_mix_directions(self):
        dispatch = self.read('top_station_dispatch_windows.csv')
        self.assertEqual(len(dispatch),15*3*5)
        # 此站的00—07时两种车型相反：普通车需补，电动车需收，不能算一个净比例。
        row=dispatch.loc[dispatch.station_id.eq('31623') & dispatch.day_type.eq('weekday')
                         & dispatch.window.eq('00–07')].iloc[0]
        self.assertEqual(row.electric_net,-28)
        self.assertEqual(row.classic_net,44)
        self.assertEqual(row.replenish_electric_share,0)
        self.assertEqual(row.recover_electric_share,1)
        for pressure, share in [('replenish_pressure_per_day','replenish_electric_share'),
                                ('recover_pressure_per_day','recover_electric_share')]:
            self.assertTrue(dispatch.loc[dispatch[pressure].eq(0),share].isna().all())
            self.assertTrue(dispatch.loc[dispatch[pressure].gt(0),share].between(0,1).all())


if __name__ == '__main__':
    unittest.main()
