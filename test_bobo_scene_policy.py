import unittest

from bobo_scene_policy import (
    FORBIDDEN_SCENE_IDS,
    SCENE_CANDIDATE_ORDER,
    eligible_scene_order,
)


class BoboScenePolicyTests(unittest.TestCase):
    def test_snowball_and_spaceship_plots_are_never_candidates(self):
        self.assertEqual(FORBIDDEN_SCENE_IDS, frozenset({5, 6}))
        for day in range(0, 400):
            for slot in (0, 1):
                candidates = eligible_scene_order(day, slot, ())
                self.assertEqual(len(candidates), len(SCENE_CANDIDATE_ORDER))
                self.assertTrue(FORBIDDEN_SCENE_IDS.isdisjoint(candidates))

    def test_recent_scenes_are_excluded(self):
        recent = {0, 1, 4}
        candidates = eligible_scene_order(12345, 0, recent)
        self.assertTrue(recent.isdisjoint(candidates))
        self.assertTrue(FORBIDDEN_SCENE_IDS.isdisjoint(candidates))

    def test_rotation_is_deterministic_and_covers_all_allowed_scenes(self):
        observed = set()
        for day in range(6):
            observed.update(eligible_scene_order(day, 0, ()))
        self.assertEqual(observed, set(SCENE_CANDIDATE_ORDER))

    def test_invalid_slot_is_rejected(self):
        with self.assertRaises(ValueError):
            eligible_scene_order(1, 2, ())


if __name__ == "__main__":
    unittest.main()
