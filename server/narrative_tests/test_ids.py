# -*- coding: utf-8 -*-
"""Tests for SII codec and trigger predicates.

ID format: 3 chars `"0SI"` where S in 1..9, I in 1..9.
"""
import pytest

from server.narrative.ids import (
    InvalidTextId,
    format_text_id,
    next_anchor_after_scene_switch,
    next_text_id,
    parse_text_id,
    should_trigger_image,
)


class TestParseTextId:
    def test_basic(self):
        assert parse_text_id("011") == (1, 1)
        assert parse_text_id("023") == (2, 3)
        assert parse_text_id("099") == (9, 9)

    def test_scene_zero_rejected(self):
        with pytest.raises(InvalidTextId):
            parse_text_id("009")

    def test_first_char_must_be_zero(self):
        # "100" -> first char '1' is not '0' (also scene=0 / scene>=10 invalid)
        with pytest.raises(InvalidTextId):
            parse_text_id("100")

    def test_image_index_zero_rejected(self):
        with pytest.raises(InvalidTextId):
            parse_text_id("010")
        with pytest.raises(InvalidTextId):
            parse_text_id("050")

    def test_wrong_length(self):
        for bad in ["", "1", "12", "1234", "01"]:
            with pytest.raises(InvalidTextId):
                parse_text_id(bad)

    def test_non_digit(self):
        for bad in ["01a", "abc", "0 1"]:
            with pytest.raises(InvalidTextId):
                parse_text_id(bad)

    def test_non_str(self):
        with pytest.raises(InvalidTextId):
            parse_text_id(11)  # type: ignore[arg-type]


class TestFormatTextId:
    def test_pad(self):
        assert format_text_id(1, 1) == "011"
        assert format_text_id(2, 9) == "029"
        assert format_text_id(9, 9) == "099"

    def test_invalid(self):
        with pytest.raises(InvalidTextId):
            format_text_id(0, 1)
        with pytest.raises(InvalidTextId):
            format_text_id(10, 1)
        with pytest.raises(InvalidTextId):
            format_text_id(1, 0)
        with pytest.raises(InvalidTextId):
            format_text_id(1, 10)


class TestNextTextId:
    def test_increment(self):
        assert next_text_id(1, 1) == "012"
        assert next_text_id(2, 8) == "029"
        assert next_text_id(9, 8) == "099"

    def test_overflow(self):
        with pytest.raises(InvalidTextId):
            next_text_id(1, 9)


class TestShouldTriggerImage:
    """The hard-required samples from the spec."""

    def test_011_to_013_triggers(self):
        assert should_trigger_image("011", "013") is True

    def test_013_to_015_triggers(self):
        assert should_trigger_image("013", "015") is True

    def test_013_to_021_does_not_trigger_cross_scene(self):
        # cross-scene resets; should_trigger_image alone returns False
        assert should_trigger_image("013", "021") is False

    def test_021_to_023_triggers(self):
        assert should_trigger_image("021", "023") is True

    def test_011_to_012_does_not_trigger(self):
        assert should_trigger_image("011", "012") is False

    def test_011_to_014_does_not_trigger(self):
        assert should_trigger_image("011", "014") is False

    def test_011_to_011_does_not_trigger(self):
        assert should_trigger_image("011", "011") is False


class TestNextAnchorAfterSceneSwitch:
    def test_basic(self):
        assert next_anchor_after_scene_switch(1) == "011"
        assert next_anchor_after_scene_switch(2) == "021"
        assert next_anchor_after_scene_switch(9) == "091"

    def test_invalid_scene(self):
        with pytest.raises(InvalidTextId):
            next_anchor_after_scene_switch(0)
        with pytest.raises(InvalidTextId):
            next_anchor_after_scene_switch(10)
