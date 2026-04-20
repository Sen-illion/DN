import unittest

from server.workflow.image_rules import should_trigger_image


class TestImageRules(unittest.TestCase):
    def test_should_trigger_image_same_scene_gap_two(self):
        self.assertTrue(should_trigger_image("013", "015"))

    def test_should_not_trigger_image_same_scene_gap_one(self):
        self.assertFalse(should_trigger_image("013", "014"))

    def test_should_trigger_image_on_scene_reset_first_anchor(self):
        self.assertTrue(should_trigger_image("013", "021"))

    def test_should_not_trigger_image_on_scene_reset_non_anchor(self):
        self.assertFalse(should_trigger_image("013", "022"))

    def test_should_trigger_image_scene_two_gap_two(self):
        self.assertTrue(should_trigger_image("021", "023"))

    def test_should_trigger_image_scene_two_next_gap_two(self):
        self.assertTrue(should_trigger_image("023", "025"))


if __name__ == "__main__":
    unittest.main()
