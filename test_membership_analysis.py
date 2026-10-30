"""验证组内分母、零计数组合和未知类别处理，防止把总量误读为偏好。"""
import unittest
import pandas as pd
from membership_analysis import membership_preference


class MembershipPreferenceTests(unittest.TestCase):
    def test_unequal_groups_use_separate_denominators(self):
        rows = [('casual', 'electric_bike')] * 3 + [('casual', 'classic_bike')]
        rows += [('member', 'electric_bike')] * 4 + [('member', 'classic_bike')] * 6
        result = membership_preference(pd.DataFrame(rows, columns=['member_casual', 'rideable_type']))
        shares = result.set_index(['member_casual', 'rideable_type']).within_membership_share
        self.assertEqual(result.rides.sum(), 14)
        self.assertAlmostEqual(shares['casual', 'electric_bike'], .75)
        self.assertAlmostEqual(shares['member', 'electric_bike'], .4)
        self.assertTrue(result.groupby('member_casual').within_membership_share.sum().eq(1).all())

    def test_zero_combo_and_absent_group(self):
        result = membership_preference(pd.DataFrame([['casual', 'electric_bike']],
                                                    columns=['member_casual', 'rideable_type']))
        indexed = result.set_index(['member_casual', 'rideable_type'])
        self.assertEqual(indexed.loc[('casual', 'classic_bike'), 'within_membership_share'], 0)
        self.assertTrue(result.loc[result.member_casual.eq('member'), 'within_membership_share'].isna().all())

    def test_missing_categories_are_not_dropped(self):
        result = membership_preference(pd.DataFrame([['casual', None], [None, 'classic_bike']],
                                                    columns=['member_casual', 'rideable_type']))
        indexed = result.set_index(['member_casual', 'rideable_type'])
        self.assertEqual(result.rides.sum(), 2)
        self.assertEqual(indexed.loc[('casual', 'unknown'), 'within_membership_share'], 1)
        self.assertEqual(indexed.loc[('unknown', 'classic_bike'), 'within_membership_share'], 1)


if __name__ == '__main__':
    unittest.main()
