"""Expected regression failures show that the review assistant actually executes tests."""

import unittest

from app import dfs_search


class GraphTests(unittest.TestCase):
    def test_integer_start_reaches_target(self):
        self.assertTrue(dfs_search({1: [2], 2: []}, 1, 2))

    def test_zero_node_can_reach_neighbor(self):
        self.assertTrue(dfs_search({0: [1], 1: []}, 0, 1))

    def test_unreachable(self):
        self.assertFalse(dfs_search({}, 0, 9))


if __name__ == "__main__":
    unittest.main()
