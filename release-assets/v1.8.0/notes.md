EVE Workshop 1.8.0 – eve-preview for Mac and Windows

## Downloads / Letöltések

- **Mac Apple Silicon:** `EVE_Muhely-1.8.0-macOS-AppleSilicon.dmg` — drag the app into Applications. Intel Macs are not supported.
- **Windows 11 x64:** `EVE_Muhely-1.8.0-Windows11-x64.zip` — extract the complete folder and run `EVE_Muhely.exe`.
- SHA-256 checksums and installation instructions are attached.

## What changed

- **eve-preview on both platforms:** live thumbnails of selected EVE windows, click-to-activate, ordered next/previous switching, configurable shortcuts recorded directly from a key field, including a single key. Unmodified/Shift-only shortcuts apply only while EVE is foreground. Thumbnail size, position, label and order persist locally.
- **Mining and damage indicators:** mining warnings appear at the right edge of the character name bar. Click a broken-crystal warning after replacing it to mark the module stopped; a subsequent logged mining activity clears that state automatically. Incoming ship damage flashes the name bar red for ten seconds. These indicators use available local EVE log events; the app does not read game memory or continuously inspect cargo levels or module state.
- **Research agents:** collect connected characters' research data in one view, project datacores available on a selected date and show Jita values. Authorize the research ESI scope for each character. Research and automatic moon-source refreshes use a daily interval.
- **Intel improvements:** regional kill notifications respect the same configured jump limit as chat intel. Improved pilot/hull parsing, cached pilot-ID preloading and compact dscan links. Names unresolved by ESI can still remain temporarily unavailable.
- **Compact production tables:** shorter column headers, a copyable total-runs value and EVE-compatible missing-material clipboard output.
- **Security hardening:** explicit HTML encoding for UI labels, translations and structured errors, safer URL handling and validated HTTP headers. CodeQL verification closed the reviewed HTML, URL and header findings. One intentional local Boost log-directory selection finding remains documented in `SECURITY_REVIEW.md`; no scanner rule was disabled and no alert was dismissed.
- Updated Hungarian and English documentation. The packages contain no characters, plans, moons, inventory, reservation history or credentials; only the public EVE Client ID is preconfigured. Existing user profiles are preserved.

## Változások magyarul

- **eve-preview Macen és Windowson:** élő klienselőnézetek, kattintásos váltás, közvetlenül felvehető következő/előző gyorsbillentyűk, akár egyetlen billentyűvel. Menthető méret, pozíció, címke és sorrend.
- **Jelzések a névcsík jobb szélén:** bányászati problémák, kézzel nyugtázható kristálycsere, új naplózott aktivitásra automatikusan törlődő szünetjelzés. Bejövő hajósebzésnél tíz másodpercig villogó névcsík. Az események játékbeli naplókból származnak, nem folyamatos cargo- vagy modulleolvasásból.
- **Research agentek:** közös RP-áttekintés, dátumra becsült datacore-mennyiség és Jita-érték, karakterenként engedélyezhető ESI-hozzáféréssel. Research- és automatikus holdadat-frissítés naponta egyszer.
- **Javított intel:** jump-határt követő killértesítések, pontosabb név- és hajófelismerés, előtöltött pilotazonosítók és rövid dscan-linkek.
- Kompaktabb gyártási táblák, másolható összes run és EVE-be illeszthető beszerzési lista.
- HTML-, fordítás-, URL- és fejléckezelési biztonsági javítások. A szándékosan választható helyi Boost-naplómappára vonatkozó egy fennmaradó CodeQL-tétel külön dokumentálva van.

## Installation and validation

Both packages use native application windows and bundled Python runtimes. Windows requires Microsoft WebView2 Runtime and .NET Framework, normally present on Windows 11. Mac supports Apple Silicon only. Neither installer has a publisher/Developer ID certificate; Mac uses mandatory local ad-hoc signing without notarization.

Close the old app before replacing its application folder. Characters, encrypted credentials, saved plans, reservations, moons and settings remain in the separate user-data directory. Updating the app does not reset it. Mac eve-preview needs Screen & System Audio Recording and Accessibility / Device Control and Data Access permissions. macOS may require granting them again after an unsigned app update. Windows uses native DWM thumbnails and window activation without macOS-style screen permission prompts. Minimized or exclusive-fullscreen game windows can limit live previews; borderless windowed mode is recommended.

Validation: **784 Python tests and 279 interface tests passed**. Mac native preview and shortcut checks passed using isolated test windows/settings. The frozen Apple Silicon backend passed EVE HTTPS certificate validation, cold startup with an empty profile, preview-mining and research routes, a 100-million-unit reaction plan, plan saving and graceful shutdown. The DMG integrity and local technical signature were verified. The Windows ZIP passed source-parity, private-data exclusion, archive, AMD64/AnyCPU and DLL import checks.

The same native Windows preview code passed GitHub Actions run [43183245650](https://github.com/Bill-web-eve/eve-workshop/actions/runs/43183245650) before release preparation, including real WebView2 windows, DWM thumbnails, activation, shortcuts, mining badges, damage indicators, overlay and application shutdown. These automated preview checks use dedicated test windows, not running EVE clients. A local Windows test with actual EVE clients has not yet been performed. Publication reruns the full application and Windows native checks for the release commit and publishes only after both succeed.

EVE Online and associated game data/trademarks belong to CCP Games. This independent fan application is not endorsed by CCP.
