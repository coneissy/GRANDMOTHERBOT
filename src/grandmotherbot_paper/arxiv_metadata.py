"""Verify the exact arXiv paper/version used by the replication."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Mapping
import xml.etree.ElementTree as ET

import requests

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
VERSION_RE = re.compile(r"(?P<id>\d{4}\.\d{4,5})(?:v(?P<version>\d+))?$")


class ArxivVerificationError(RuntimeError):
    """Raised when arXiv metadata cannot prove the requested paper identity."""


@dataclass(frozen=True)
class ArxivPaperMetadata:
    arxiv_id: str
    version: str
    title: str
    authors: tuple[str, ...]
    published: datetime
    updated: datetime
    entry_id: str


@dataclass(frozen=True)
class ArxivVerification:
    expected_identifier: str
    actual_identifier: str
    title_match: bool
    authors_match: bool
    published_match: bool
    updated_match: bool

    @property
    def version_match(self) -> bool:
        return self.expected_identifier == self.actual_identifier

    @property
    def passed(self) -> bool:
        return all((
            self.version_match,
            self.title_match,
            self.authors_match,
            self.published_match,
            self.updated_match,
        ))

    def as_dict(self) -> dict[str, object]:
        return {
            "expected_identifier": self.expected_identifier,
            "actual_identifier": self.actual_identifier,
            "version_match": self.version_match,
            "title_match": self.title_match,
            "authors_match": self.authors_match,
            "published_match": self.published_match,
            "updated_match": self.updated_match,
            "status": "PASS" if self.passed else "FAIL",
        }


def parse_identifier(identifier: str) -> tuple[str, str]:
    value = identifier.rstrip("/").rsplit("/", 1)[-1]
    match = VERSION_RE.fullmatch(value)
    if not match:
        raise ArxivVerificationError(f"Invalid arXiv identifier: {identifier!r}")
    version = match.group("version") or "1"
    return match.group("id"), f"v{version}"


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_api_response(xml_text: str) -> ArxivPaperMetadata:
    root = ET.fromstring(xml_text)
    entries = root.findall("atom:entry", ATOM_NS)
    if len(entries) != 1:
        raise ArxivVerificationError(
            f"Expected exactly one arXiv entry, received {len(entries)}"
        )

    entry = entries[0]
    entry_id = (entry.findtext("atom:id", namespaces=ATOM_NS) or "").strip()
    base_id, version = parse_identifier(entry_id)
    title = " ".join((entry.findtext("atom:title", namespaces=ATOM_NS) or "").split())
    if not title:
        raise ArxivVerificationError("arXiv response did not contain a title")

    authors = tuple(
        " ".join((author.findtext("atom:name", namespaces=ATOM_NS) or "").split())
        for author in entry.findall("atom:author", ATOM_NS)
    )
    if not authors or any(not author for author in authors):
        raise ArxivVerificationError("arXiv response did not contain valid authors")

    published = _parse_datetime(
        (entry.findtext("atom:published", namespaces=ATOM_NS) or "").strip()
    )
    updated = _parse_datetime(
        (entry.findtext("atom:updated", namespaces=ATOM_NS) or "").strip()
    )

    return ArxivPaperMetadata(
        arxiv_id=base_id,
        version=version,
        title=title,
        authors=authors,
        published=published,
        updated=updated,
        entry_id=entry_id,
    )


def fetch_metadata(
    identifier: str,
    *,
    session: requests.Session | None = None,
    timeout: float = 20.0,
) -> ArxivPaperMetadata:
    base_id, version = parse_identifier(identifier)
    query_id = base_id if version == "v1" else f"{base_id}{version}"
    client = session or requests.Session()
    response = client.get(
        ARXIV_API_URL,
        params={"id_list": query_id},
        headers={"User-Agent": "GrandMotherBot/0.2 arXiv provenance verifier"},
        timeout=timeout,
    )
    response.raise_for_status()
    metadata = parse_api_response(response.text)
    expected = f"{base_id}{version}"
    actual = f"{metadata.arxiv_id}{metadata.version}"
    if actual != expected:
        raise ArxivVerificationError(f"arXiv returned {actual}, expected {expected}")
    return metadata


def verify_metadata(
    metadata: ArxivPaperMetadata,
    expected: Mapping[str, object],
) -> ArxivVerification:
    expected_id = str(expected["identifier"])
    expected_title = " ".join(str(expected["title"]).split())
    expected_authors = tuple(str(author) for author in expected["authors"])
    expected_published_raw = str(expected["published"])
    expected_updated_raw = str(expected["updated"])
    expected_published = datetime.fromisoformat(expected_published_raw)
    expected_updated = datetime.fromisoformat(expected_updated_raw)
    published_match = (
        metadata.published.date() == expected_published.date()
        if len(expected_published_raw) == 10
        else metadata.published == expected_published
    )
    updated_match = (
        metadata.updated.date() == expected_updated.date()
        if len(expected_updated_raw) == 10
        else metadata.updated == expected_updated
    )

    return ArxivVerification(
        expected_identifier=expected_id,
        actual_identifier=f"{metadata.arxiv_id}{metadata.version}",
        title_match=metadata.title == expected_title,
        authors_match=metadata.authors == expected_authors,
        published_match=published_match,
        updated_match=updated_match,
    )


def verify_identifier(
    identifier: str,
    expected: Mapping[str, object],
    *,
    session: requests.Session | None = None,
) -> ArxivVerification:
    return verify_metadata(fetch_metadata(identifier, session=session), expected)


def load_manifest(path: str = "config/paper_manifest.yaml") -> dict[str, object]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
