# EVE Műhely

Helyben futó, magyar nyelvű EVE Online gyártástervező macOS Apple Silicon és Windows 11 x64 rendszerhez. A felület a saját böngésződben nyílik meg: **http://127.0.0.1:8765**.

## Letöltés

A telepíthető csomagok a [GitHub Kiadások / Releases](https://github.com/Bill-web-eve/eve-workshop/releases) oldalon érhetők el a közzétételi munkafolyamat sikeres futása után. A jelenlegi csomagok: **Mac Apple Silicon 0.10.0**, **Windows 11 x64 0.10.0**, magyar és angol felülettel, holdnyilvántartással.

A helyi repositoryból történő automatikus közzététel lépései: [release-assets/README.md](release-assets/README.md).

## Mit tud?

- Több karakter személyes készlete, blueprintjei és gyártási munkái EVE ESI kapcsolattal.
- Corporation készletek és munkák, corporationönként elkülönített tervezéssel.
- Gyártási és reakcióláncok, hátralévő runok, alapanyaghiány és gráfos nézet.
- Mentett tervek készlet- és BPC-run-foglalással, valamint összesített beszerzési listával.
- BPO/BPC ME, TE, példányszám és run kezelése; kézi beállítási lehetőségek.
- Struktúrabónuszok és tervenként választott karakter skilljeivel számolt gyártási idő.
- Skill- és tanulási sor figyelése, PI-áttekintés, sötét mód, rendezhető és szűrhető táblázatok.

## Használat

Az oldalsávban, a sötét mód kapcsolója alatt a **Magyar / English** gombokkal válthatsz nyelvet. A választást a böngésző megjegyzi; a nyelv a megnyitott nézetben is azonnal változik. A beírt értékek, szűrők és még nem mentett módosítások megmaradnak. A karakterek, corporationök, mentett tervek és EVE-tárgyak neve nem változik.

A kész alkalmazás futtatásához nem kell Excel, Codex vagy külön Python. Windowson a teljes ZIP kibontása után indítsd az `EVE_Muhely.exe` fájlt; Macen másold a DMG-ben található alkalmazást az Alkalmazások mappába. A kiadások aláírás és hitelesítés nélkül készülnek. A Windows-csomag tényleges Windows 11 alatti futtatása ezen a fejlesztői gépen még nem volt ellenőrizhető; a mellékelt `Ellenorzes.cmd` külön, ideiglenes profillal ellenőrzi a működést.

A saját karaktereidet az **EVE-kapcsolat** menüben adhatod hozzá. A kiadások nem tartalmaznak karaktert, mentett tervet, készletet vagy belépési tokent; csak a nyilvános EVE Client ID lehet előre beállítva. Forrásból indításkor saját Client ID is megadható. Részletes útmutató: [Hasznalat.md](Hasznalat.md).

A GitHub-tároló a forráskódot, teszteket, fordítási eszközöket és a CCP nyilvános SDE-adataiból készített katalógust tartalmazza. A személyes profilok és a kész alkalmazáscsomagok nem részei a forráskódnak. Az EVE Online és a kapcsolódó játékadatok a CCP Games tulajdonát képezik; ez a projekt nem hivatalos CCP-termék.

Local Hungarian EVE Online industry planner. Developer and build notes follow below.

## Development

- Python 3.9+; runtime dependency: `cryptography` (SSO token signatures and encryption).
- Run: `python3 run.py --no-browser` then open `http://127.0.0.1:8765`.
- Test: `python3 -m unittest discover -s tests -v` (binds loopback ports).
- UI tests: `npm ci --ignore-scripts` then `npm test`. Node and jsdom are developer-only dependencies; neither is needed to run the app.
- `EVE_MUHELY_DATA` overrides the user-data directory; keep test data separate from personal data.
- The bundled SQLite catalogue is generated from CCP's official JSONL SDE. Rebuild with `python3 tools/build_catalog.py --help`, or update through the UI.
- Plain browser JavaScript/CSS; no frontend build and no remote scripts.
- Displayed item names use the shared `itemName` renderer and delegated copy handling. Clipboard API writes only text/plain, with a selection-preserving textarea fallback. Existing search/detail/graph actions are preserved; graph nodes also support keyboard copying.
- `tools/publish_macos.py DESTINATION --install-local` copies sources, builds a native macOS launcher with code/catalogue inside its Resources, and installs it to `~/Applications` with a Desktop symlink. Building requires Apple's Command Line Tools; running does not. User data and credentials are never copied. The local installation avoids protected cloud-folder execution at startup.

## Boundaries

The production planner covers manufacturing and reactions. Net stock and WIP once per type, after aggregated parent demand. PI production scheduling, invention, ISK and slot scheduling are outside this version. Fuel inputs default to buy; explicit build/buy overrides supported. BPCs with different ME/TE are not pooled. Job/run capacity warnings do not suppress full material-demand planning.

Saved plans reserve the stock and active-job output they actually consume. Allocations rebuild from one snapshot in activation order; each saved plan can use its own allocations, and drafts subtract every active allocation. Completed components replace their raw-material holds. Editing an older plan previews its priority effect on later plans before save. Source/location/character and blueprint settings remain shared. The additive schema migration preserves legacy plans as unreserved until activation. Since 0.8.0, BPC run capacity is also reserved by blueprint item ID within the plan's stock owner.

The interactive production graph uses the same calculated rows and positive material edges as the queue. It has no independent recipe or stock calculations. Shared types are single nodes, covered branches stay pruned, and purchase/covered nodes are optional. `static/graph.js` contains the pure layout and branch-selection code; `app.js` handles the SVG, zoom/pan, keyboard selection and detail tables. No external graph library, network request or frontend build is needed.

Skill monitoring (`muhely/skills.py`, `static/skills.js`, `/api/skills`) includes every connected character independently of production filters. Skill and queue snapshots commit as a pair; `resource_status` keeps their errors/authorization separate from industry data. Existing industry-only tokens still refresh with their original scopes. New SSO consent includes both skill scopes and verifies the selected character on reauthorization. Skills use Cache-Control and conditional ETag revalidation (60-second local ceiling), not the legacy Expires header. Completed queue entries update trained levels/SP without guessing active Alpha/Omega levels. A red status means idle; amber means the first interruption in continuous training is within 120 hours. Missing/failed/over-five-minute data stays unknown. The foreground skill page refreshes once per minute while open; there is no background scheduler or OS notification.

The tests include synthetic graph and SSO cases, local HTTP integration, and the two prior verified Excel baselines. Live SSO requires a user-owned public Client ID and login; no Client Secret is needed for PKCE.

PI monitoring (`muhely/pi.py`, `static/pi.js`, `/api/pi?hours=24`) lists every connected character and their colonies. Separate atomic `pi` snapshots/status preserve industry and skills on API failure. The GET-only ESI colony calls use `esi-planets.manage_planets.v1`, conditional ETags and a 600-second local cache ceiling. Feature-specific reauthorization preserves existing grants without requiring unrelated new scopes. Official SDE planetary schematics supply input/output quantities and cycles; a packaged fallback also supports older user catalogues.

PI supply uses factory-local buffers and a route-constrained bipartite maximum flow over existing storage stocks, counting shared stock once. It checks the next cycle and 1/6/24/72-hour horizons, reports finite stock coverage, missing outputs, expired extraction programs and full stores. Upstream extraction/production is dependency evidence, never fabricated inventory. Link bandwidth, import scheduling, future extraction yield and continuous production simulation are not modeled. ESI advances colony information only when viewed in game: timestamps stay visible, factory snapshots older than 30 minutes and failed/stale HTTP data stay unknown. No game changes or external notifications occur.

Saved-plan shortcuts replace the fixed sample products. They open the actual saved ID, quantity and ownership context. `/api/plans/shopping` previews all saved goals against one stock/WIP pool: active reservations retain priority, unreserved goals follow in creation order using remaining stock without persistent activation. It reuses the production allocation pass and aggregates positive purchase shortages by type with per-plan contributions. The all-plans view is independent of the current unsaved target, supports CSV/clipboard and invalidates after state reloads. Tests cover shared stock, active/inactive ordering, no mutation, completed Archon pruning, WIP, deletion and endpoint authentication.

`desktop.py` is the frozen desktop entry point. It starts the bundled server process and opens the user's browser; it never installs Python or packages on the recipient's Mac. `tools/build_macos_release.py` uses PyInstaller in an isolated development environment and an allowlisted source stage. Only `client_id` is allowed in `data/defaults.json`; no user database, vault, character or plan is copied. A fresh browser also starts with an empty product selection. Existing user data and an explicitly saved Client ID continue to override bundle defaults.

To rebuild an Apple Silicon distribution on a Mac, install `requirements.txt`, `pyinstaller==6.22.3` and `certifi==2026.7.22` into a dedicated Python environment, then run `python tools/build_macos_release.py --client-id-file PUBLIC_CLIENT_JSON --work-dir EMPTY_BUILD_DIR --output-dir RELEASE_DIR`. The public JSON only needs `client_id`; never pass an encrypted vault or user database. The current build uses Python 3.12.14 and cryptography 46.0.7, targets arm64/macOS 11+, and creates a verified DMG with installation instructions and a SHA-256 checksum. Developer ID and notarization are omitted; mandatory ad-hoc signing remains. No Gatekeeper setting or quarantine attribute is modified. The private, already-installed local app is not replaced by this release build.

Delivery-cache reconciliation uses `AssetSnapshotPending`, preserving affected character/type timestamps and the asset cache expiry through allocation and HTTP responses. It never credits delivered job output on top of stale assets. Only still-missing outputs from matching manufacturing/reaction recipes block; already-covered outputs do not. Saved plans/holds remain unchanged. The foreground UI displays the dated wait and retries EVE sync after cache expiry, with a minimum one-minute retry interval, without bypassing ESI caching. Fast cached sync completion also recalculates the plan. Integration tests cover pending saved/combined plans, persistence, manual/location filters, matching recipe metadata, covered outputs and exact-once release after fresh assets.

Table controls (`static/tables.js`) enhance every shared table with stable natural/numeric sorting, canonical timestamp metadata, per-column AND filters, and character dropdowns. DOM rows are moved rather than rebuilt to retain editors and handlers; the third sort click restores source order. Runtime view state survives rerenders and combines with legacy search. `node --test tests/test_tables.cjs` checks quantity/date/text ordering and matching.

Corporation planning (`muhely/corporations.py`, `static/corporations.js`): optional read-only corp consent, public membership discovery, and one atomic assets/blueprints/jobs snapshot per corporation. Providers are tried in turn; personal industry errors and tokens stay separate. New plans carry nullable `corporation_id`; legacy NULL is personal. Contexts, inventory/parameter overrides, location filters, reservations and combined shopping are partitioned by owner. An unavailable corporation never falls back to personal stock or blocks unrelated personal plans. Corporation planning reads its asset/job revision in one SQLite transaction. Clean distributions still contain only the public Client ID and catalogue.

0.8.0: reactions accept up to 100 million output units with compressed job batches. Grouped quantity inputs preserve integer validation. Procurement includes missing BPC runs and noncopyable reaction formulas; saved plans reserve existing BPC capacity by item ID within their own stock owner. Production times use active ESI skills and SDE requirements/bonuses, with per-plan character selection and an explicit manual fallback. Implants and copying/invention job inputs are outside the duration/procurement model.

## Windows 11 x64 portable release

`tools/build_windows_release.py` builds a clean ZIP on macOS or Windows. It uses the official Python 3.13.16 x64 embeddable distribution, Windows wheels pinned in `tools/windows-runtime-lock.json`, and a small Unicode Win32 GUI launcher compiled with Zig 0.15.2. Build dependencies are Python, Pillow and Zig. Download URLs and SHA-256 hashes are pinned to python.org/PyPI release metadata; recipient machines need no Python, package manager, Excel, Codex or administrator installation.

Build with `python tools/build_windows_release.py --client-id-file PUBLIC_CLIENT_JSON --work-dir EMPTY_BUILD_DIR --output-dir RELEASE_DIR --cache-dir DEPENDENCY_CACHE --zig PATH_TO_ZIG`. Only allowlisted app source, static files, catalogue and the public Client ID are staged. The package audit rejects user databases, vault files and logs; all `.exe`, `.dll` and `.pyd` files must be AMD64 PE32+. The launcher is a GUI executable, not a console application. No publisher certificate is supplied and no Windows protection is disabled.

Windows stores profiles under `%LOCALAPPDATA%\EVE Muhely`. `muhely/windows_security.py` protects the Fernet vault key with current-user Windows DPAPI and fixed application entropy. It does not use machine-wide protection or a plaintext-key fallback. Existing legacy plaintext keys are verified against the encrypted token file before migrating. Failure to decrypt never replaces the vault. macOS continues to use Keychain; POSIX fallback behaviour is unchanged.

`windows_desktop.py` writes startup diagnostics and calls the common desktop entry point. Windows backend processes run without a console and with isolated Python paths; source/catalogue SQLite connections close before replacement so SDE updates work with Windows file locking. `windows_smoke_test.py` plus `Ellenorzes.cmd` run a recipient-side smoke test against a temporary blank profile: actual DPAPI, HTTP/CSRF, large reaction planning, plan persistence and optional public EVE HTTPS. It never logs in a real character or changes the user's plans. Windows runtime execution has not been verified on this build host; `release-manifest.json` records that limitation explicitly.

## Interface languages (0.9.0)

Hungarian is the default. The sidebar language buttons persist `eve-muhely-language` locally, independently of the theme. `static/i18n.js` projects canonical Hungarian presentation messages using the English catalogue in `static/i18n-en.js`. It updates existing text and accessibility attributes in place, including asynchronous content, without rerendering forms, making requests or changing API values. Known messages can contain numbered placeholders; captured names are preserved, and `:t` explicitly opts a captured UI fragment into recursive translation. Unknown messages are kept intact. Date presentation follows the selected language; quantities retain their requested three-digit space grouping.

Names and other user-controlled labels must use `verbatim`, `data-i18n-skip` or the dedicated name renderers. Input values, select values, data attributes, credentials, EVE names and clipboard contents remain canonical. `EveI18n.t` also localizes confirmation messages, validation and CSV headings. No translation service or external script is used. Tests cover preference persistence, live changes, DOM updates, names, escaping, dates, table filters, input identity and 100-million-unit validation.


## Holdak és kitermelés / Moons (0.10.0)

A **Holdak és kitermelés** menüben kézzel rögzíthetők a holdak: kereshető rendszerlista, automatikus ESI-csillagkép, valódi holdválasztó, Athanor vagy Metenox, legfeljebb négy érc és százalékos aránya. A rendszerek, holdak és ércadatok a CCP nyilvános SDE-jéből előre elérhetők; a kiválasztott rendszert és csillagképet az ESI ellenőrzi. A nyilvános ESI-adatot 90 napig tároljuk, ETaggel frissítjük, hiba esetén az utolsó adatot vagy az SDE-t jelölve megtartjuk. Külön **Rendszeradatok ellenőrzése** gomb is van.

Az öt nézet: nyilvántartás; 30 napos termelés holdanként, összesen és struktúránként; fogyasztás; kristálytípusok és érctérfogat-arányok; számítási beállítások. A táblázatok rendezhetők és becsukható szűrősort kaptak. A nyilvántartás közös a helyi profilban, nem a kiválasztott gyártási kör készlete. A becslés nem ír jóvá anyagot a készletben.

Számítás: 720 óra × 30 000 m³/óra × a megadott ércarány. Az arányokat nem normalizáljuk: a hiányos összetételből csak az ismert ércek számítanak. A két tizedesből eredő kerekítési eltérést 100,02%-ig elfogadjuk; ennél nagyobb összeggel a hold menthető, de termelése és kristályaránya javításig kimarad. A működő fúró fogyasztása ilyenkor is számít.

Athanor: nullsec T2 riges Tatara, minden finomítási skill V, alapértelmezetten 4%-os implant: `0.53 × 1.055 × 1.12 × 1.15 × 1.10 × 1.10 × 1.04 = 90.628105568%`. Teljes SDE szerinti finomítási adagokkal, anyagonként lefelé kerekítve, holdanként külön számolunk. Az implant és a begyűjtési arány szerkeszthető. A 100%-os begyűjtés a teljes ismert alapércmennyiség finomításának felső becslése. A tényleges bányászati veszteség, állásidő, jackpot, gazdag ércváltozat és kritikus találat nincs külön modellezve.

Metenox: az SDE-ben szereplő 40%-os hatékonyságot, órás ciklust és 200 Magmatic Gas/ciklus fogyasztást használja; a finomítási skillek, implant és kézi begyűjtési arány nem hatnak rá. A havi termelés a lefelé kerekített órás becslés 720-szorosa. Csak holdanyagok keletkeznek, standard ásványok (Pyerite, Mexallon) nem. Mindkét fúró 5 Fuel Block/óra. A bekapcsolás külön mező: Athanor 360, Metenox 1000 Fuel Block/alkalom; az alapérték nulla. Más szolgáltatások és a külön Tatara üzemanyaga nincs beleszámítva.

A kristályfül az SDE megfelelő feldolgozási skillje alapján párosítja a 20 alapércet az öt holdérckategóriához. A I/II, B I/II, C I/II változat választható; az alapérték A II. A százalék a megadott, bányászandó érctérfogatok aránya az adott holdon, illetve az összes beszámítható Athanoron. Nem kristálydarabszám vagy kopásbecslés; Metenoxhoz nincs kristályigény.

A kiadási csomagban nincs hold, karakter, mentett terv vagy saját készlet. A kézzel felvitt holdak a felhasználó saját `muhely.sqlite3` adatbázisában maradnak. Az SDE frissítése a holdakat megőrzi.

Források: [CCP SDE](https://developers.eveonline.com/docs/services/static-data/), [Moon Mining](https://support.eveonline.com/hc/en-us/articles/115005404229-Moon-Mining), [Metenox](https://www.eveonline.com/news/view/equinox-expansion-notes), [aktuális Magmatic Gas fogyasztás](https://www.eveonline.com/news/view/patch-notes-version-23-01), [Tatara 5,5%](https://www.eveonline.com/news/view/patch-notes-version-20-03), [Resources Realigned](https://www.eveonline.com/news/view/resources-realigned).
