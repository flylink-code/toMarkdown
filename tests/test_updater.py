""""Tests for GitHub release update parsing."""

from __future__ import annotations

import sys

import pytest

from tomarkdown.updater import UpdateError, is_installed_build, is_newer_version, parse_release


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


def test_parse_release_returns_installer_url_separately() -> None:
    release = parse_release(
        {
            "tag_name": "v0.6.3",
            "assets": [
                {"name": "toMarkdown-v0.6.3-windows-x64-setup.exe", "browser_download_url": "https://example.com/setup.exe"},
                {"name": "toMarkdown-v0.6.3-windows-x64.zip", "browser_download_url": "https://example.com/app.zip"},
            ],
        },
        current="0.6.2",
    )
    assert release is not None
    assert release.download_url == "https://example.com/app.zip"
    assert release.installer_url == "https://example.com/setup.exe"


def test_parse_release_without_installer_has_empty_installer_url() -> None:
    release = parse_release(
        {
            "tag_name": "v0.6.3",
            "assets": [{"name": "toMarkdown-v0.6.3-windows-x64.zip", "browser_download_url": "https://example.com/app.zip"}],
        },
        current="0.6.2",
    )
    assert release is not None
    assert release.installer_url == ""


def test_is_installed_build_detects_uninstaller(tmp_path, monkeypatch) -> None:
    exe = tmp_path / "toMarkdown.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert not is_installed_build()
    (tmp_path / "Uninstall.exe").write_bytes(b"")
    assert is_installed_build()


def test_is_installed_build_false_when_not_frozen(tmp_path, monkeypatch) -> None:
    (tmp_path / "Uninstall.exe").write_bytes(b"")
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "python.exe"))
    assert not is_installed_build()


def test_parse_release_ignores_current_or_unsupported_release() -> None:
    assert parse_release({"tag_name": "v0.4.0", "assets": []}, current="0.4.0") is None
    assert parse_release({"tag_name": "v0.5.0", "assets": []}, current="0.4.0") is None

