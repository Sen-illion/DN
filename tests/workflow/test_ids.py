import unittest

from server.workflow.ids import next_text_id, parse_text_id


class TestIds(unittest.TestCase):
    def test_next_text_id_start(self):
        self.assertEqual(next_text_id(1, None), "101")

    def test_next_text_id_increment(self):
        self.assertEqual(next_text_id(2, 1), "202")

    def test_parse_text_id_supports_legacy_zero_prefixed_examples(self):
        parsed = parse_text_id("013")
        self.assertEqual(parsed.scene_id, 1)
        self.assertEqual(parsed.image_index_in_scene, 3)


if __name__ == "__main__":
    unittest.main()
