EVE Workshop 1.4.0 – native Mac and Windows apps

Downloads

- **Apple Silicon Mac (M1 or later):** `EVE_Muhely-1.4.0-macOS-AppleSilicon.dmg`
- **Windows 11 64-bit:** `EVE_Muhely-1.4.0-Windows11-x64.zip`

Both packages open in their own application window and include Hungarian and English interfaces. The Mac package supports Apple Silicon only. Windows requires Microsoft Edge WebView2 Runtime. No separate Python, Excel or Codex installation is needed.

What is new

- Configure a local market hub and read its private structure order book with an authorized character. Use Jita or local buy, sell and split prices independently for materials and selling.
- Compact per-plan production costs, expected selling revenue, seller skills/standings, sales tax, broker fee, net proceeds and profit. Structure broker fees are entered manually; an explicit zero is supported as a provisional estimate.
- Four independent hauling rates: Jita import/export and local market import/export. Import uses packaged procurement volume; export uses newly planned finished output. Both are included in production costs.
- Unspecified BPC costs count as zero with a visible note; production covered by BPOs has zero blueprint cost without that note.
- Export the entire moon register as JSON, bulk import backups, or paste one or more in-game moon survey tables. Preview before applying; existing moons can be skipped or updated. Rescans preserve rent and drill settings. Invalid or stale imports never partly modify the register.
- Native Mac JSON save/open dialogs and updated Hungarian/English user guides.

Existing local data

Stop the old application before replacing its program folder. Your existing characters, plans, moon register, settings and encrypted EVE authorizations remain in the separate local profile directory:

- macOS: `~/Library/Application Support/EVE Muhely/`
- Windows: `%LOCALAPPDATA%\EVE Muhely`

Distributions contain no characters, saved plans, personal inventory, moon records or authorization tokens. Only the public EVE Client ID is preconfigured. Moving to another computer or Windows user account requires EVE authorization again.

The Mac app has no Developer ID signature or notarization; it carries only the required local ad-hoc signature. The Windows package is portable and has no publisher certificate. See the included platform installation instructions and SHA-256 files.

---

**Magyar:** új helyi market árazás, teljes gyártási költség és profit, külön Jita/helyi import–export díjak, tömeges holdexport és játékbeli scanimport. Mindkét csomag saját ablakban fut. Frissítéskor a külön tárolt helyi adatok megmaradnak; a kiadás nem tartalmaz személyes adatot. A Mac-csomag Apple Siliconra, a Windows-csomag Windows 11 x64-re készült.
