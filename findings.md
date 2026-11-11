# Findings

- v0.6.1 ultimately published MSI assets, but repeated WiX failures motivated the requested NSIS migration.
- NSIS can provide the required directory page, optional shortcut sections, uninstaller, and icon without harvesting the PyInstaller tree.
- GitHub CLI authentication is active for account `flylink-code` using SSH for Git operations.
- Historical failures were caused by PowerShell variable escaping and WiX harvested-file path binding; the current committed workflow fixed those older issues.
- The application updater intentionally continues to use the portable ZIP asset, so NSIS changes do not require updater code changes.
