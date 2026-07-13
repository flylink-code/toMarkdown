""""Tests for GitHub release update parsing."""

from __future__ import annotations

import pytest

from tomarkdown.updater import UpdateError, is_newer_version, parse_release


def test_is_newer_version_pads_missing_parts() -> None:
    assert is_newer_version("v0.4.1", "0.4")
    assert not is_newer_version("0.4.0", "0.4")


def test_is_newer_version_rejects_invalid_version() -> None:
    with pytest.raises(UpdateError, match="Invalid release version"):
        is_newer_version("latest", "0.4.0")


def test_parse_release_returns_matching_windows_archive() -> None:
    release = parse_release(
        {
            "tag_name": "v0.5.0",
            "assets": [
                {"name": "checksums.txt", "browser_download_url": "https://example.com/checksums"},
                {"name": "toMarkdown-v0.5.0-windows-x64.zip", "browser_download_url": "https://example.com/toMarkdown.zip"},
            ],
        },
        current="0.4.0",
    )
    assert release is not None
    assert release.version == "0.5.0"


def test_parse_release_ignores_current_or_unsupported_release() -> None:
    assert parse_release({"tag_name": "v0.4.0", "assets": []}, current="0.4.0") is None
    assert parse_release({"tag_name": "v0.5.0", "assets": []}, current="0.4.0") is None

