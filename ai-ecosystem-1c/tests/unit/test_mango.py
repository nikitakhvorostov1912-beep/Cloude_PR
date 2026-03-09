"""Tests for Mango Office webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from integrations.telephony.mango import (
    parse_mango_event,
    verify_mango_signature,
)
from integrations.telephony.audio_stream import validate_call_id


class TestMangoSignature:
    def test_valid_signature(self) -> None:
        api_key = "test-key"
        json_data = '{"call_id": "test"}'
        salt = "test-salt"
        sign = hashlib.sha256((api_key + json_data + salt).encode()).hexdigest()
        assert verify_mango_signature(
            api_key, json_data, sign, expected_key=api_key, api_salt=salt
        )

    def test_invalid_signature(self) -> None:
        assert not verify_mango_signature(
            "test-key", '{"data": 1}', "invalid-sign",
            expected_key="test-key", api_salt="salt",
        )

    def test_wrong_api_key(self) -> None:
        assert not verify_mango_signature(
            "wrong-key", '{"data": 1}', "sign",
            expected_key="correct-key", api_salt="salt",
        )


class TestParseMangoEvent:
    def test_parse_incoming_event(self) -> None:
        raw_json = json.dumps({
            "entry_id": "mango-call-001",
            "from": {"number": "+74951234567"},
            "to": {"number": "+74957654321"},
            "call_state": "appeared",
        })
        event = parse_mango_event(raw_json)
        assert event.call_id == "mango-call-001"
        assert event.from_number == "+74951234567"

    def test_parse_with_missing_fields_uses_defaults(self) -> None:
        raw_json = json.dumps({"call_id": "test"})
        event = parse_mango_event(raw_json)
        assert event.call_id == "test"


class TestValidateCallId:
    def test_valid_call_ids(self) -> None:
        assert validate_call_id("call-001")
        assert validate_call_id("mango-abc-123")
        assert validate_call_id("a1b2c3")

    def test_invalid_call_ids(self) -> None:
        assert not validate_call_id("")
        assert not validate_call_id("a" * 200)
        assert not validate_call_id("call id with spaces")
