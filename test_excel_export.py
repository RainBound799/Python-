"""核对Excel与CSV的完整对应关系，以及嵌图是否遮挡数据。"""
from pathlib import Path
import hashlib
import unittest
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries
from excel_export import SHEETS


class ExcelExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = Path(__file__).resolve().parent/'output'
        if not (cls.out/'分析结果汇总.xlsx').exists():
            raise unittest.SkipTest('先运行analysis.py，再检查Excel输出')

    def test_all_csv_values_and_images_are_preserved(self):
        book = load_workbook(self.out/'分析结果汇总.xlsx')
        try:
            self.assertEqual(book.sheetnames, ['结果目录']+[x[0] for x in SHEETS])
            for title, csv_name, figure, _ in SHEETS:
                with self.subTest(sheet=title):
                    frame = pd.read_csv(self.out/csv_name, dtype={'station_id':'string'})
                    sheet = book[title]
                    _, header, cols, last = range_boundaries(sheet.auto_filter.ref)
                    self.assertEqual(last-header, len(frame))
                    self.assertEqual(cols, len(frame.columns))
                    for row, expected in zip(sheet.iter_rows(min_row=header+1, max_row=last, max_col=cols),
                                             frame.itertuples(index=False, name=None)):
                        for field, cell, value in zip(frame.columns, row, expected):
                            if pd.isna(value):
                                self.assertIsNone(cell.value)
                            elif field in ['date', 'started_at']:
                                self.assertEqual(pd.Timestamp(cell.value), pd.Timestamp(value))
                            elif isinstance(value, str):
                                self.assertEqual(cell.value, value)
                                self.assertEqual(cell.data_type, 's')
                            else:
                                self.assertAlmostEqual(cell.value, value, places=8)
                    self.assertEqual(len(sheet._images), int(figure is not None))
                    if figure:
                        picture = sheet._images[0]
                        self.assertEqual(hashlib.sha256(picture._data()).digest(),
                                         hashlib.sha256((self.out/'figures'/figure).read_bytes()).digest())
                        height_px = picture.anchor.ext.cy/9525
                        reserved_px = sum((sheet.row_dimensions[r].height or 15)*4/3
                                          for r in range(picture.anchor._from.row+1, header))
                        self.assertGreater(reserved_px, height_px)
        finally:
            book.close()

    def test_membership_hourly_matches_other_aggregations(self):
        hourly = pd.read_csv(self.out/'membership_hourly.csv').set_index('hour')
        overall = pd.read_csv(self.out/'hourly_demand.csv').set_index('hour')
        profile = pd.read_csv(self.out/'user_vehicle_profile.csv')
        self.assertEqual(len(hourly), 24)
        pd.testing.assert_series_equal(hourly.sum(axis=1), overall.rides, check_names=False)
        self.assertEqual(hourly.sum().to_dict(), profile.groupby('member_casual').rides.sum().to_dict())


if __name__ == '__main__':
    unittest.main()
