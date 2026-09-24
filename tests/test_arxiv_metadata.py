from datetime import datetime, timezone

import pytest

from grandmotherbot_paper.arxiv_metadata import (
    ArxivVerificationError,
    parse_api_response,
    parse_identifier,
    verify_metadata,
)


XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2507.13023v3</id>
    <updated>2025-08-04T00:00:00Z</updated>
    <published>2025-07-17T00:00:00Z</published>
    <title>Measuring CEX-DEX Extracted Value and Searcher Profitability: The Darkest of the MEV Dark Forest</title>
    <author><name>Fei Wu</name></author>
    <author><name>Danning Sui</name></author>
    <author><name>Thomas Thiery</name></author>
    <author><name>Mallesh Pai</name></author>
  </entry>
</feed>
"""


def test_parse_identifier():
    assert parse_identifier("2507.13023v3") == ("2507.13023", "v3")
    assert parse_identifier("http://arxiv.org/abs/2507.13023v3") == ("2507.13023", "v3")


def test_parse_api_response():
    metadata = parse_api_response(XML)
    assert metadata.arxiv_id == "2507.13023"
    assert metadata.version == "v3"
    assert metadata.authors == ("Fei Wu", "Danning Sui", "Thomas Thiery", "Mallesh Pai")
    assert metadata.published == datetime(2025, 7, 17, tzinfo=timezone.utc)
    assert metadata.updated == datetime(2025, 8, 4, tzinfo=timezone.utc)


def test_verify_metadata_passes():
    metadata = parse_api_response(XML)
    expected = {
        "identifier": "2507.13023v3",
        "title": metadata.title,
        "authors": list(metadata.authors),
        "published": "2025-07-17T00:00:00+00:00",
        "updated": "2025-08-04T00:00:00+00:00",
    }
    result = verify_metadata(metadata, expected)
    assert result.passed
    assert result.as_dict()["status"] == "PASS"


def test_verify_metadata_rejects_wrong_version():
    metadata = parse_api_response(XML)
    expected = {
        "identifier": "2507.13023v4",
        "title": metadata.title,
        "authors": list(metadata.authors),
        "published": "2025-07-17T00:00:00+00:00",
        "updated": "2025-08-04T00:00:00+00:00",
    }
    result = verify_metadata(metadata, expected)
    assert not result.passed
    assert not result.version_match


def test_parse_api_response_requires_one_entry():
    with pytest.raises(ArxivVerificationError):
        parse_api_response('<feed xmlns="http://www.w3.org/2005/Atom"/>')
