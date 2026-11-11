# Findings

- v0.6.1 ultimately published MSI assets, but repeated WiX failures motivated the requested NSIS migration.
- NSIS can provide the required directory page, optional shortcut sections, uninstaller, and icon without harvesting the PyInstaller tree.
- GitHub CLI authentication is active for account `flylink-code` using SSH for Git operations.
- Historical failures were caused by PowerShell variable escaping and WiX harvested-file path binding; the current committed workflow fixed those older issues.
- Since v0.6.3 the updater downloads `*-windows-x64-setup.exe` for installed builds (Program Files needs elevation, so the zip+robocopy path fails there) and keeps the zip flow for portable copies.
