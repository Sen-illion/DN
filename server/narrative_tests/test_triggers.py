# -*- coding: utf-8 -*-
"""Tests for triggers (image trigger / user choice / scene switch plan)."""
import pytest

from server.narrative.triggers import (
    ChoicePruneDecision,
    ImageTriggerDecision,
    SceneSwitchPlan,
    evaluate_image_trigger,
    on_user_choice,
    plan_scene_switch,
    should_prepare_next_scene,
)


class TestEvaluateImageTrigger:
    def test_first_anchor_when_no_prior(self):
        d = evaluate_image_trigger(None, "011")
        assert d.should_trigger is True
        assert d.anchor_text_id == "011"
        assert d.reason == "first-anchor-in-scene"

    def test_first_anchor_when_empty_prior(self):
        d = evaluate_image_trigger("", "011")
        assert d.should_trigger is True

    def test_same_scene_gap_2_triggers(self):
        d = evaluate_image_trigger("011", "013")
        assert d.should_trigger is True
        assert d.anchor_text_id == "013"
        assert d.reason == "gap-equals-2"

    def test_same_scene_gap_1_does_not_trigger(self):
        d = evaluate_image_trigger("011", "012")
        assert d.should_trigger is False
        assert d.anchor_text_id is None

    def test_cross_scene_resets_and_triggers(self):
        d = evaluate_image_trigger("013", "021")
        assert d.should_trigger is True
        assert d.anchor_text_id == "021"
        assert d.reason == "scene-switched-reset"

    def test_walk_full_sequence_scene1(self):
        # Spec example: 011 -> 013 -> 015
        anchor = "011"
        for cur, expected in [("012", False), ("013", True), ("014", False), ("015", True)]:
            d = evaluate_image_trigger(anchor, cur)
            assert d.should_trigger is expected, f"failed at {cur}"
            if d.should_trigger:
                anchor = d.anchor_text_id

    def test_walk_full_sequence_scene2_after_switch(self):
        # 021 -> 023 -> 025
        anchor = "021"
        for cur, expected in [("022", False), ("023", True), ("024", False), ("025", True)]:
            d = evaluate_image_trigger(anchor, cur)
            assert d.should_trigger is expected, f"failed at {cur}"
            if d.should_trigger:
                anchor = d.anchor_text_id


class TestOnUserChoice:
    def test_basic_prune(self):
        d = on_user_choice("011", ["b1", "b2", "b3"], "b2")
        assert isinstance(d, ChoicePruneDecision)
        assert d.chosen_branch_id == "b2"
        assert sorted(d.abandoned_branch_ids) == ["b1", "b3"]

    def test_single_branch(self):
        d = on_user_choice("011", ["only"], "only")
        assert d.abandoned_branch_ids == []

    def test_invalid_choice_raises(self):
        with pytest.raises(ValueError):
            on_user_choice("011", ["b1", "b2"], "b3")


class TestPlanSceneSwitch:
    def test_switch_1_to_2(self):
        p = plan_scene_switch(1)
        assert isinstance(p, SceneSwitchPlan)
        assert p.from_scene == 1
        assert p.to_scene == 2
        assert p.next_anchor_text_id == "021"

    def test_switch_8_to_9(self):
        p = plan_scene_switch(8)
        assert p.next_anchor_text_id == "091"

    def test_cannot_switch_past_9(self):
        with pytest.raises(ValueError):
            plan_scene_switch(9)
        with pytest.raises(ValueError):
            plan_scene_switch(0)


class TestShouldPrepareNextScene:
    def test_below_min(self):
        assert should_prepare_next_scene(3, min_rounds=5, max_rounds=6) is False

    def test_at_min(self):
        assert should_prepare_next_scene(5, min_rounds=5, max_rounds=6) is True

    def test_at_max(self):
        assert should_prepare_next_scene(6, min_rounds=5, max_rounds=6) is True

    def test_negative(self):
        assert should_prepare_next_scene(-1, min_rounds=5, max_rounds=6) is False
