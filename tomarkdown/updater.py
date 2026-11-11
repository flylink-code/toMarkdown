"""GitHub release discovery and Windows in-place update support."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tomarkdown import __version__

GITHUB_REPOSITORY = "flylink-code/toMarkdown"
GITHUB_LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
WINDOWS_ARCHIVE_SUFFIX = "-windows-x64.zip"
WINDOWS_INSTALLER_SUFFIX = "-windows-x64-setup.exe"
UNINSTALLER_NAME = "Uninstall.exe"


class UpdateError(RuntimeError):
    """Raised when an update cannot be checked, downloaded, or installed."""


@dataclass(frozen=True)
class ReleaseInfo:
    """The installable Windows assets from a GitHub release."""

    version: str
    download_url: str
    release_url: str
    installer_url: str = ""


def _version_key(version: str) -> tuple[int, ...]:
    """Return a comparable numeric version key for semantic version strings."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", version.strip())
    if not match:
        raise UpdateError(f"Invalid release version: {version}")
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(candidate: str, current: str = __version__) -> bool:
    """Whether candidate is numerically newer than current."""
    candidate_key = _version_key(candidate)
    current_key = _version_key(current)
    width = max(len(candidate_key), len(current_key))
    return candidate_key + (0,) * (width - len(candidate_key)) > current_key + (0,) * (width - len(current_key))


def parse_release(payload: dict[str, object], current: str = __version__) -> ReleaseInfo | None:
    """Extract a newer Windows x64 archive from a GitHub release response."""
    tag_name = str(payload.get("tag_name", ""))
    version = tag_name.removeprefix("v")
    if not is_newer_version(version, current):
        return None

    assets = payload.get("assets", [])
    if not isinstance(assets, list):
        raise UpdateError("GitHub release assets are invalid.")
    archive_url = ""
    installer_url = ""
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", ""))
        url = str(asset.get("browser_download_url", ""))
        if not url.startswith("https://"):
            continue
        if name.endswith(WINDOWS_ARCHIVE_SUFFIX):
            archive_url = archive_url or url
        elif name.endswith(WINDOWS_INSTALLER_SUFFIX):
            installer_url = installer_url or url
    if not archive_url:
        return None
    return ReleaseInfo(version, archive_url, str(payload.get("html_url", "")), installer_url)


def is_installed_build() -> bool:
    """Whether the running app was set up by the NSIS installer (not a portable copy)."""
    if not getattr(sys, "frozen", False):
        return False
    return (Path(sys.executable).resolve().parent / UNINSTALLER_NAME).is_file()


def check_for_update(current: str = __version__, opener: Callable[..., object] = urllib.request.urlopen) -> ReleaseInfo | None:
    """Fetch the latest GitHub release and return it when it is newer."""
    request = urllib.request.Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "toMarkdown-updater"},
    )
    try:
        with opener(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Unable to check GitHub releases: {exc}") from exc
    if not isinstance(payload, dict):
        raise UpdateError("GitHub returned an invalid release response.")
    return parse_release(payload, current)


def _extract_archive(archive: Path, destination: Path) -> Path:
    """Extract archive contents while rejecting paths outside the staging directory."""
    try:
        with zipfile.ZipFile(archive) as package:
            root = destination.resolve()
            for member in package.infolist():
                target = (destination / member.filename).resolve()
                if os.path.commonpath((str(root), str(target))) != str(root):
                    raise UpdateError("Update archive contains an unsafe path.")
            package.extractall(destination)
    except (OSError, zipfile.BadZipFile) as exc:
        raise UpdateError(f"Unable to unpack update: {exc}") from exc
    executable = destination / "toMarkdown.exe"
    if not executable.is_file():
        raise UpdateError("Update archive does not contain toMarkdown.exe.")
    return executable


def _download(url: str, destination: Path) -> None:
    """Stream url into destination."""
    request = urllib.request.Request(url, headers={"User-Agent": "toMarkdown-updater"})
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def _run_detached(script: Path) -> None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(["cmd.exe", "/c", str(script)], creationflags=flags)


def _install_with_setup(release: ReleaseInfo, executable: Path) -> None:
    """Run the NSIS installer silently after the app exits (UAC elevates it)."""
    if not release.installer_url:
        raise UpdateError(
            "This release has no installer package. Please download it manually from "
            f"{release.release_url or 'the GitHub releases page'}."
        )
    work_dir = Path(tempfile.mkdtemp(prefix="toMarkdown-update-"))
    setup = work_dir / "setup.exe"
    try:
        _download(release.installer_url, setup)
        if setup.stat().st_size == 0:
            raise UpdateError("Downloaded installer is empty.")
    except (OSError, UpdateError) as exc:
        raise UpdateError(f"Unable to download update: {exc}") from exc

    pid = os.getpid()
    script = work_dir / "install-update.cmd"
    # `start /wait` goes through ShellExecute, so the installer's admin manifest triggers UAC.
    script.write_text(
        "@echo off\r\n"
        ":wait\r\n"
        f'tasklist /fi "PID eq {pid}" /fi "IMAGENAME eq {executable.name}" /nh | find /i "{executable.name}" >nul\r\n'
        "if not errorlevel 1 (\r\n  timeout /t 1 /nobreak >nul\r\n  goto wait\r\n)\r\n"
        f'start "" /wait "{setup}" /S\r\n'
        f'start "" "{executable}"\r\n'
        f'rmdir /s /q "{work_dir}"\r\n',
        encoding="utf-8",
    )
    _run_detached(script)


def download_and_install(release: ReleaseInfo) -> None:
    """Download an update and schedule replacement after the app exits."""
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        raise UpdateError("Automatic installation is available only in the Windows release app.")

    executable = Path(sys.executable).resolve()
    if is_installed_build():
        _install_with_setup(release, executable)
        return

    install_dir = executable.parent
    work_dir = Path(tempfile.mkdtemp(prefix="toMarkdown-update-"))
    archive = work_dir / "update.zip"
    staging_dir = work_dir / "files"
    staging_dir.mkdir()
    try:
        _download(release.download_url, archive)
        _extract_archive(archive, staging_dir)
    except (OSError, UpdateError) as exc:
        raise UpdateError(f"Unable to download update: {exc}") from exc

    script = work_dir / "install-update.cmd"
    script.write_text(
        "@echo off\r\ntimeout /t 2 /nobreak >nul\r\n"
        + f'robocopy "{staging_dir}" "{install_dir}" /E /IS /IT >nul\r\n'
        + f'start "" "{executable}"\r\nrmdir /s /q "{work_dir}"\r\n',
        encoding="utf-8",
    )
    _run_detached(script)

