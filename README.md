# EVE Műhely

Helyben futó, magyar–angol nyelvű EVE Online gyártástervező macOS Apple Silicon és Windows 11 x64 rendszerhez. Mindkét platformon saját alkalmazásablakban nyílik meg. A helyi szolgáltatás címe: **http://127.0.0.1:8765**.

## Letöltés

A telepíthető csomagok a [GitHub Kiadások / Releases](https://github.com/Bill-web-eve/eve-workshop/releases) oldalon érhetők el a közzétételi munkafolyamat sikeres futása után. A jelenlegi csomagok: **Mac Apple Silicon 1.5.0**, **Windows 11 x64 1.5.0**, magyar és angol felülettel, élő kill/intel jelzésekkel, flottajelentésekkel és gyártástervezéssel.

A helyi repositoryból történő automatikus közzététel lépései: [release-assets/README.md](release-assets/README.md).

## Mit tud?

- Több karakter személyes készlete, blueprintjei és gyártási munkái EVE ESI kapcsolattal.
- Corporation készletek és munkák, corporationönként elkülönített tervezéssel.
- Gyártási és reakcióláncok, hátralévő runok, alapanyaghiány és gráfos nézet.
- Mentett tervek készlet- és BPC-run-foglalással, valamint összesített beszerzési listával.
- BPO/BPC ME, TE, példányszám és run kezelése; kézi beállítási lehetőségek.
- Struktúrabónuszok és tervenként választott karakter skilljeivel számolt gyártási idő.
- Skill- és tanulási sor figyelése, PI-áttekintés időalapú termelési becsléssel, sötét mód, rendezhető és szűrhető táblázatok.
- Jita buy/sell/split alapanyagárak, termékeladási érték, ESI-rendszerindex és beállítható ipari díjak.
- Választható helyi station/struktúra market buy/sell/split árakkal, külön ESI-olvasóval; a privát piac gyorsítótára elkülönül Jitától és más olvasóktól.
- Kompakt tervenkénti bekerülés/bevétel/profit, független anyag- és eladási árforrással, Accounting/standing alapú NPC-díjakkal, megadható struktúra broker fee-vel és egyéb költségekkel.
- Holdankénti termelés, üzemanyag-, bérleti és egyéb költségek, összesített 30 napos profit.

## Az 1.5.0 kiadás újdonságai

- Személyes és corporation-szerződések külön nézetben, karakter/corp és kiadási dátum szerinti szűréssel, tétellistával és helyi állapotelőzményekkel.
- Értesítés új, közvetlenül karakternek vagy corporationnek címzett szerződésről és saját kiadott szerződés elfogadásáról. Az első import nem küld régi értesítéseket. Az ESI 30 napos és folyamatban lévő listájából beolvasott adatok később is megmaradnak a helyi archívumban.
- Új szerződésengedélyek a Beállítások → Adathozzáférések alatt. A kikapcsolt corporationökhöz nem indul szerződéslekérés; automatikusan legfeljebb 15 percenként ellenőriz az alkalmazás.
- Karakterenként kapcsolható implantérték-figyelés: kidokkoláskor figyelmeztet, ha az aktív klón implantjainak ismert értéke meghaladja a megadott határt. Új ESI-engedély és külön bekapcsolás szükséges.
- A Mac intel overlay az EVE-re kattintáskor is megmarad a beállított lejáratig. Magyar–angol felületi és Mac-menüfordítások javítva.
- A főablak bezárása a teljes alkalmazást leállítja; javított Windowsos leállásellenőrzés. Készletnézet: állapotválasztó szűrő, helynevek, keskenyebb mennyiségoszlop; állítható 25/50/100 soros táblázatok.

## Az 1.4.1 kiadás újdonságai

- Windowson is elérhető az átlátszó intel overlay: keret nélküli, felül maradó ablak, amely nem veszi el a billentyűzet fókuszát és normál módban átengedi a kattintásokat.
- Monitoronként menthető pozíció, húzható elhelyezési minta, 1–3600 másodperces megjelenítési idő, magyar–angol felület és sötét/világos téma.
- Az intelértesítések kikapcsolása az overlayt is azonnal elrejti. A jelentések az eredeti időpontjuk alapján járnak le; egy frissítés nem hosszabbítja meg őket.
- Valódi Windowsos ellenőrzés az overlay kirajzolására, fókuszkezelésére, kattintásátengedésére, lejáratára és bezárására. Az EVE keret nélküli ablakos módja támogatott; exkluzív teljes képernyős játék és a Windows biztonsági képernyői eltakarhatják az overlayt.

## Az 1.4.0 kiadás újdonságai

- Helyi nullsec market beállítása: rendszer- és struktúraválasztás, olvasási ESI-engedélyek, Jita és helyi buy/sell/split árazás.
- Kompakt, tervenként mentett költség- és bevételösszesítés: anyag, blueprint, job cost, egyéb költség, eladói skillek/standingek, adók és nettó profit.
- Külön Jita import/export és helyi market import/export ISK/m³ szállítási díjak, csomagolt anyag- és készterméktérfogattal.
- A meg nem adott BPC-költség nullával számol, látható jelzéssel; a BPO-val fedezett gyártás blueprintköltsége nulla.
- A teljes holdnyilvántartás JSON exportja és tömeges visszaimportja, játékbeli moon scan beillesztése több holdra, előnézettel és atomi mentéssel.
- A scanfrissítés megőrzi a meglévő bérletet és struktúrát; a hold-, bolygó-, rendszer- és ércazonosítókat ellenőrzi. A Mac saját ablakában natív JSON mentés és fájlbetöltés működik.
- Magyar–angol dokumentáció, valamint személyes adat nélküli Mac Apple Silicon és Windows 11 x64 csomag. Frissítéskor a külön tárolt helyi profil megmarad.

## Az 1.3.0 kiadás újdonságai

- Karakterenkénti kill- és lossnapló, flottamenetek, megfigyelt ESI-pozíciók és útvonalak, rendszerenkénti harci időablakok és ISK-összesítések.
- Kettő–négy oldalra bontott harci jelentések: a résztvevők besorolása a harci kapcsolatok alapján történik, kézzel módosítható. A veszteségek hajótípusonként összegezhetők; a hajóikonok a killmailre vezetnek.
- Élő zKillboard-adatfolyam mentett folytatási ponttal, csoportosított régiós killjelzésekkel és térképjelölőkkel. Az értesítések ISK-érték helyett a rendszert és a hajókat mutatják.
- Külön kapcsolható intelértesítések, önálló térkép- és chatablak, kompakt jelentéskártyák és frissítés közben is használható régióválasztó.
- Tervtől független keresés minden személyes és corporation item között; az In progress nézet személyes összesítése minden karakterre is kérhető.
- Corporationönként kikapcsolható adatfigyelés és legalább 15 perces automatikus ESI-frissítési időköz; a kifejezett kézi frissítés és a külön engedélyezett pozíciókövetés kivétel.
- Pontosabb PI-kitermelési időzítők, bolygónként elkülönített gyári készletbecslés és a holdnaptár hiányzó hozzáféréseinek érthetőbb jelzései.
- Részletes magyar és angol dokumentáció; tiszta Mac- és Windows-csomag személyes adatok nélkül. A közzététel csak a teljes alkalmazásteszt és a Windows WebView2-futtatási próba sikeres befejezése után indul.

## Az 1.2.0 kiadás újdonságai

- A Windows-verzió is saját ablakban fut: WebView2-felület, natív vágólap, fájl- és mappaválasztás, nyomtatás, külön intel-térkép és intelchat.
- Az EVE engedélyezése a rendszerböngészőben történik; utána a kiválasztott alkalmazásnézet marad nyitva.
- Téma és nyelv a Settings alatt, külön engedélyezhető Windows-rendszerértesítések, figyelmeztetés nem mentett módosításokra és futó lekérésekre bezáráskor.
- Rögzített, ellenőrzött Windows-függőségek; sikeres Windowsos futtatási próba a tényleges beépített Python és WebView2 használatával. A hibásan hiányzó WebView2-keresőkönyvtárak javítva.
- A Mac Apple Silicon-verzió továbbra is saját ablakos. Az átlátszó inteloverlay jelenleg csak Macen támogatott.

## Az 1.1.0 kiadás újdonságai

- Önálló Mac-alkalmazás Cocoa/WKWebView ablakkal és beépített futtatókörnyezettel; külön rendszer- és intelchatablakok, OS-értesítések és állítható inteloverlay. A Windows-kiadás továbbra is böngészős.
- Intelchat-fájlok követése, teljes régiós térkép, ugrástávolság szerinti jelzések, clear-kezelés, pilóták zKillboard-hivatkozása és hajóikonok. A jelentéskártyák három perc után eltűnnek.
- Személyes és corporation értesítési központ: tanulás, kész jobok, PI és közelgő holdkitermelések. Látható lekérdezési állapotok és adatfrissítési szakaszok.
- Bányászati napló karakterenként, ércenként és naponta, megőrzött előzményekkel, térfogattal és finomított Jita-értékkel. Nyersérc-árazás és residue-számítás nincs.
- Karakterenként egyetlen „Authorize all access” jóváhagyással kérhető minden támogatott ESI-jogosultság.
- Csak repackagelt készlet számít gyártáshoz; javított tervszámítási visszajelzések és készletfrissítési határidők, folyamatban lévő jobok az idővonalon, nézetet megőrző tervváltás és kompaktabb elrendezés.

## Az 1.0.0 kiadás újdonságai

- **Gyártásütemező:** karakterenkénti aktív skillek és fizikai blueprintek, külön gyártási és reakciós slotkeret, anyagfüggőségek és érkezési idők. Kizárólag meglévő BPO/BPC vagy további beszerzést is megengedő mód.
- **Áttekinthető idővonal:** karakterszűrés, állítható látható napok (alapból 7), előző/következő időszak, teljes időtáv, jobrészletek és CSV-export. Állítható minimum jobhossz (alapból 12 óra), kötelező jobközi várakozás nélkül.
- **Moon management:** holdnyilvántartás, 30 napos termelés, fogyasztás és profit, ércértesítések és ESI kitermelési naptár, 1–9 közötti kristályarányok és helyi naptárfeliratkozás.
- **Accountok és tanulás:** kézi accountcsoportok, Omega/MCT-lejáratok és tanulási helyek; a nem tanítható karakterek nem kapnak indokolatlan üres-sor figyelmeztetést.
- **Közös beállítások:** struktúrák, EVE-kapcsolat, adathozzáférések, holdszámítás, naptárszinkron és accountok egy lenyitható menüben.
- **Beszerzés:** EVE Multibuy formátumú egyedi és közös lista, BPO/BPC-k nélkül; hiányzó blueprintrunok külön jelölve.
- **Dokumentáció:** teljes magyar és angol kézikönyv a bal oldali menü alján, kereséssel, tartalomjegyzékkel, letöltéssel és nyomtatás/PDF lehetőséggel.
- A korábbi Jita buy/sell/split árak, ipari díjak, PI-előrejelzések, corporation elkülönítés, foglalások, sötét mód és táblázatszűrők megmaradtak. A kész jobokat külön figyelmeztetés jelzi.

A teljes útmutató: [Magyar](Hasznalat.md) · [English](UserGuide.en.md). A kiadás üres profilt tartalmaz; a meglévő saját helyi adatok frissítéskor megmaradnak.

## Használat

A **Settings → Appearance and language** oldalon válthatsz sötét/világos témát és magyar/angol nyelvet. A választást az alkalmazásablak vagy a böngésző megjegyzi; a nyelv a megnyitott nézetben is azonnal változik. A beírt értékek, szűrők és még nem mentett módosítások megmaradnak. A karakterek, corporationök, mentett tervek és EVE-tárgyak neve nem változik.

A kész alkalmazás futtatásához nem kell Excel, Codex vagy külön Python. Windowson a teljes ZIP kibontása után indítsd az `EVE_Muhely.exe` fájlt; Macen másold a DMG-ben található alkalmazást az Alkalmazások mappába. A kiadások aláírás és hitelesítés nélkül készülnek. A Windows-csomag tényleges Windows 11 alatti futtatása ezen a fejlesztői gépen még nem volt ellenőrizhető; a mellékelt `Ellenorzes.cmd` külön, ideiglenes profillal ellenőrzi a működést.

A saját karaktereidet az **EVE-kapcsolat** menüben adhatod hozzá. A kiadások nem tartalmaznak karaktert, mentett tervet, készletet vagy belépési tokent; csak a nyilvános EVE Client ID lehet előre beállítva. Forrásból indításkor saját Client ID is megadható. Részletes útmutató: [Hasznalat.md](Hasznalat.md).

A GitHub-tároló a forráskódot, teszteket, fordítási eszközöket és a CCP nyilvános SDE-adataiból készített katalógust tartalmazza. A személyes profilok nem részei a tárolónak. Az ellenőrzött telepítőcsomagokat a release-assets mappa tartalmazza az automatikus közzétételhez. Az EVE Online és a kapcsolódó játékadatok a CCP Games tulajdonát képezik; ez a projekt nem hivatalos CCP-termék.

Local Hungarian/English EVE Online industry planner. Developer and build notes follow below.

## Development

- Python 3.9+; runtime dependencies: `cryptography` (SSO token signatures and encryption) and `certifi` (HTTPS certificate bundle).
- Run: `python3 run.py --no-browser` then open `http://127.0.0.1:8765`.
- Test: `python3 -m unittest discover -s tests -v` (binds loopback ports).
- UI tests: `npm ci --ignore-scripts` then `npm test`. Node and jsdom are developer-only dependencies; neither is needed to run the app.
- `EVE_MUHELY_DATA` overrides the user-data directory; keep test data separate from personal data.
- The bundled SQLite catalogue is generated from CCP's official JSONL SDE. Rebuild with `python3 tools/build_catalog.py --help`, or update through the UI.
- Plain browser JavaScript/CSS; no frontend build and no remote scripts.
- Displayed item names use the shared `itemName` renderer and delegated copy handling. Clipboard API writes only text/plain, with a selection-preserving textarea fallback. Existing search/detail/graph actions are preserved; graph nodes also support keyboard copying.
- `tools/publish_macos.py DESTINATION --install-local` copies sources, builds a native macOS launcher with code/catalogue inside its Resources, and installs it to `~/Applications` with a Desktop symlink. Building requires Apple's Command Line Tools; running does not. User data and credentials are never copied. The local installation avoids protected cloud-folder execution at startup.

## Boundaries

The production planner covers manufacturing and reactions. Net stock and WIP once per type, after aggregated parent demand. The separate scheduler assigns manufacturing/reaction slots and physical blueprints with material dependencies. PI forecasts are estimates, not an import/hauling schedule; invention and copying research jobs are not scheduled. ISK estimates use Jita prices and configurable industry fees. Fuel inputs default to buy; explicit build/buy overrides supported. BPCs with different ME/TE are not pooled. Job/run capacity warnings do not suppress full material-demand planning.

Saved plans reserve the stock and active-job output they actually consume. Allocations rebuild from one snapshot in activation order; each saved plan can use its own allocations, and drafts subtract every active allocation. Completed components replace their raw-material holds. Editing an older plan previews its priority effect on later plans before save. Source/location/character and blueprint settings remain shared. The additive schema migration preserves legacy plans as unreserved until activation. Since 0.8.0, BPC run capacity is also reserved by blueprint item ID within the plan's stock owner.

The interactive production graph uses the same calculated rows and positive material edges as the queue. It has no independent recipe or stock calculations. Shared types are single nodes, covered branches stay pruned, and purchase/covered nodes are optional. `static/graph.js` contains the pure layout and branch-selection code; `app.js` handles the SVG, zoom/pan, keyboard selection and detail tables. No external graph library, network request or frontend build is needed.

Skill monitoring (`muhely/skills.py`, `static/skills.js`, `/api/skills`) includes every connected character independently of production filters. Skill and queue snapshots commit as a pair; `resource_status` keeps their errors/authorization separate from industry data. Existing industry-only tokens still refresh with their original scopes. New SSO consent includes both skill scopes and verifies the selected character on reauthorization. Skills use Cache-Control and conditional ETag revalidation (60-second local ceiling), not the legacy Expires header. Completed queue entries update trained levels/SP without guessing active Alpha/Omega levels. A red status means idle; amber means the first interruption in continuous training is within 120 hours. Missing/failed/over-five-minute data stays unknown. The foreground skill page refreshes once per minute while open; background checks and OS alerts are available through the opt-in macOS notification center.

The tests include synthetic graph and SSO cases, local HTTP integration, and the two prior verified Excel baselines. Live SSO requires a user-owned public Client ID and login; no Client Secret is needed for PKCE.

PI monitoring (`muhely/pi.py`, `static/pi.js`, `/api/pi?hours=24`) lists every connected character and their colonies. Separate atomic `pi` snapshots/status preserve industry and skills on API failure. The GET-only ESI colony calls use `esi-planets.manage_planets.v1`, conditional ETags and a 600-second local cache ceiling. Feature-specific reauthorization preserves existing grants without requiring unrelated new scopes. Official SDE planetary schematics supply input/output quantities and cycles; a packaged fallback also supports older user catalogues.

PI supply uses factory-local buffers and a route-constrained bipartite maximum flow over existing storage stocks, counting shared stock once. It checks the next cycle and 1/6/24/72-hour horizons, reports finite stock coverage, missing outputs, expired extraction programs and full stores. Upstream extraction/production is dependency evidence, never fabricated inventory. A separate snapshot-anchored forecast estimates varying extraction yield and routed factory production. Link bandwidth and future imports are not scheduled. ESI advances colony information only when viewed in game: timestamps stay visible, factory snapshots older than 30 minutes and failed/stale HTTP data stay unknown. No game changes occur; reliable stops and dated forecasts can feed the opt-in notification center.

Saved-plan shortcuts replace the fixed sample products. They open the actual saved ID, quantity and ownership context. `/api/plans/shopping` previews all saved goals against one stock/WIP pool: active reservations retain priority, unreserved goals follow in creation order using remaining stock without persistent activation. It reuses the production allocation pass and aggregates positive purchase shortages by type with per-plan contributions. The all-plans view is independent of the current unsaved target, supports CSV/clipboard and invalidates after state reloads. Tests cover shared stock, active/inactive ordering, no mutation, completed Archon pruning, WIP, deletion and endpoint authentication.

`desktop.py` is the frozen Mac backend entry point, wrapped in the native Cocoa/WKWebView shell. Windows uses `windows_desktop.py` and native WinForms/WebView2 windows. Neither package installs Python or packages on the recipient's machine. `tools/build_macos_release.py` uses PyInstaller in an isolated development environment and an allowlisted source stage. Only `client_id` is allowed in `data/defaults.json`; no user database, vault, character or plan is copied. A fresh profile starts with an empty product selection. Existing user data and an explicitly saved Client ID continue to override bundle defaults.

To rebuild an Apple Silicon distribution on a Mac, install `requirements.txt`, `pyinstaller==6.22.3` and `certifi==2026.7.22` into a dedicated Python environment, then run `python tools/build_macos_release.py --client-id-file PUBLIC_CLIENT_JSON --work-dir EMPTY_BUILD_DIR --output-dir RELEASE_DIR`. The public JSON only needs `client_id`; never pass an encrypted vault or user database. The current build uses Python 3.12.14 and cryptography 46.0.7, targets arm64/macOS 11+, and creates a verified DMG with installation instructions and a SHA-256 checksum. Developer ID and notarization are omitted; mandatory ad-hoc signing remains. No Gatekeeper setting or quarantine attribute is modified. The private, already-installed local app is not replaced by this release build.

Delivery-cache reconciliation uses `AssetSnapshotPending`, preserving affected character/type timestamps and the asset cache expiry through allocation and HTTP responses. It never credits delivered job output on top of stale assets. Only still-missing outputs from matching manufacturing/reaction recipes block; already-covered outputs do not. Saved plans/holds remain unchanged. The foreground UI displays the dated wait and retries EVE sync after cache expiry, with a minimum one-minute retry interval, without bypassing ESI caching. Fast cached sync completion also recalculates the plan. Integration tests cover pending saved/combined plans, persistence, manual/location filters, matching recipe metadata, covered outputs and exact-once release after fresh assets.

Table controls (`static/tables.js`) enhance every shared table with stable natural/numeric sorting, canonical timestamp metadata, per-column AND filters, and character dropdowns. DOM rows are moved rather than rebuilt to retain editors and handlers; the third sort click restores source order. Runtime view state survives rerenders and combines with legacy search. `node --test tests/test_tables.cjs` checks quantity/date/text ordering and matching.

Corporation planning (`muhely/corporations.py`, `static/corporations.js`): optional read-only corp consent, public membership discovery, and one atomic assets/blueprints/jobs snapshot per corporation. Providers are tried in turn; personal industry errors and tokens stay separate. New plans carry nullable `corporation_id`; legacy NULL is personal. Contexts, inventory/parameter overrides, location filters, reservations and combined shopping are partitioned by owner. An unavailable corporation never falls back to personal stock or blocks unrelated personal plans. Corporation planning reads its asset/job revision in one SQLite transaction. Clean distributions still contain only the public Client ID and catalogue.

0.8.0: reactions accept up to 100 million output units with compressed job batches. Grouped quantity inputs preserve integer validation. Procurement includes missing BPC runs and noncopyable reaction formulas; saved plans reserve existing BPC capacity by item ID within their own stock owner. Production times use active ESI skills and SDE requirements/bonuses, with per-plan character selection and an explicit manual fallback. Implants and copying/invention job inputs are outside the duration/procurement model.

## Native macOS application (1.1.0)

`tools/build_macos_release.py` packages the native Cocoa/WKWebView shell in `tools/macos_launcher.m` with a frozen `eve-backend` executable. The shell starts that bundled executable, so recipients need no developer runtime. Developer installations made with `tools/publish_macos.py DESTINATION --install-local` retain the source/runtime launcher fallback. Both paths preserve the user profile.

Appearance and language controls are under Settings. `static/desktop.js` supplies the platform adapter for clipboard, CSV/ICS/Markdown save dialogs, printing, external links, OAuth return and quit. Native messages are accepted only from the main frame at the exact local origin; local APIs retain session and CSRF protection. EVE login uses a ten-minute one-use browser handoff and authenticated result polling. OAuth codes and tokens are not returned to JavaScript. Closing the window checks pending work and gracefully stops the local service.

The generated `static/app-window-icon.png` and `static/app-window.icns` combine the existing amber cube with the EVE wordmark; the image-generation prompt is retained alongside them. The existing release icons remain available. `tests/macos_window_smoke.m` exercises real WKWebView against a temporary synthetic App profile (never port 8765), including preferences, plan switching, clipboard/export adapters, an offline mocked OAuth round trip and graceful shutdown.

## Windows 11 x64 portable release

`tools/build_windows_release.py` builds a clean ZIP on macOS or Windows. It uses the official Python 3.13.16 x64 embeddable distribution, Windows wheels pinned in `tools/windows-runtime-lock.json`, and a small Unicode Win32 GUI launcher compiled with Zig 0.15.2. Build dependencies are Python, Pillow and Zig. Download URLs and SHA-256 hashes are pinned to python.org/PyPI release metadata; recipient machines need no Python, package manager, Excel, Codex or administrator installation.

Build with `python tools/build_windows_release.py --client-id-file PUBLIC_CLIENT_JSON --work-dir EMPTY_BUILD_DIR --output-dir RELEASE_DIR --cache-dir DEPENDENCY_CACHE --zig PATH_TO_ZIG`. Only allowlisted app source, static files, catalogue and the public Client ID are staged. The package audit rejects user databases, vault files and logs; all `.exe`, `.dll` and `.pyd` files must be AMD64 PE32+. The launcher is a GUI executable, not a console application. No publisher certificate is supplied and no Windows protection is disabled.

Windows stores profiles under `%LOCALAPPDATA%\EVE Muhely`. `muhely/windows_security.py` protects the Fernet vault key with current-user Windows DPAPI and fixed application entropy. It does not use machine-wide protection or a plaintext-key fallback. Existing legacy plaintext keys are verified against the encrypted token file before migrating. Failure to decrypt never replaces the vault. macOS continues to use Keychain; POSIX fallback behaviour is unchanged.

`windows_desktop.py` writes startup diagnostics and calls the common desktop entry point. Windows backend processes run without a console and with isolated Python paths; source/catalogue SQLite connections close before replacement so SDE updates work with Windows file locking. `windows_smoke_test.py` plus `Ellenorzes.cmd` run a recipient-side smoke test against a temporary blank profile: actual DPAPI, HTTP/CSRF, large reaction planning, plan persistence and optional public EVE HTTPS. It never logs in a real character or changes the user's plans. The 1.2.0 pinned embedded runtime and real WebView2 window passed the Windows-hosted CI smoke test, including clipboard, export, OAuth return, separate map/chat windows and graceful shutdown. This Mac build host does not itself execute Windows binaries.

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


### Release upload recovery

The publication workflow verifies and reconciles every reviewed `release-assets/v*/manifest.json` in numeric version order. It repairs missing installers on older mutable releases as well as publishing the latest version. Creation uses the REST response's numeric release ID directly; uploads and final publication checks also use IDs, so a freshly created draft need not appear in the release listing or tag index. Existing assets are SHA-256 checked and never overwritten. A draft is published only after every required asset has uploaded and verified successfully. An interrupted run resumes on the next push or manual workflow run.


## A 0.11.0 kiadás újdonságai

Jita-árazás a holdtermelés, a gyártási terv és az egyedi/összesített beszerzési lista mellé. A táblázaton kívül választható **Jita sell**, **Jita buy**, **Jita split**; a választást a böngésző megjegyzi. Forrás: a CCP nyilvános ESI API-ja, The Forge régió (10000002), kizárólag a Jita IV - Moon 4 - Caldari Navy Assembly Plant állomás (60003760). Buy = legmagasabb vételi ajánlat, sell = legalacsonyabb eladási ajánlat, split = ezek számtani átlaga. A lekérés nem igényel karakterengedélyt és nem ad fel megbízást.

A termékenkénti, összes oldalt feldolgozó árlekérés háttérben fut. A helyi cache és az ETag megmarad újraindítás után; az ötperces lekérési korlátot a frissítés gomb is betartja. Oldalhiba esetén a korábbi teljes ár marad meg, régi árként megjelölve. Hiányzó vételi/eladási oldal nem kap nulla értéket, a splithez mindkét ár kell. A részösszeg mellett megjelenik az árazatlan tételek száma. A BPC-runokat nem árazzuk BPO-piaci árral.

Az anyagköltség a hátralévő gyártás felhasználandó bemeneteinek értéke, beleértve a készleten lévő és folyamatban lévő komponenseket. A legyártandó köztes termékek értékét nem adjuk hozzá még egyszer a bemeneteik értékéhez; a már elkészült komponensek alapanyagai nem kerülnek vissza a számításba. A beszerzési érték csak a hiányzó mennyiségekkel számol. A holdtermelés értéke a kiválasztott struktúraszűrővel, 30 napra számolt termékek értéke. Az egységárak tájékoztató jellegűek, mennyiségi árkönyvmélységet nem számolunk. A rendszer indexét és a gyártási díjakat külön job cost számítás kezeli.

A pénzszámítás négy tizedes egységárból, egész aritmetikával készül; a sorösszeg cent pontosságra kerekített, az összesítés a látható sorösszegek összege. Az ár nélküli sorok `–` értékkel jelennek meg. A hiánylisták CSV-exportja tartalmazza az árazási módot, egységárat és értéket is.

A **Production by moon** és **Ore volume and processing** holdoszlopai pontos választólistás szűrést kaptak, a szűrősor továbbra is csukva indul. Az angol figyelmeztetések javítva; a karakter-, hold- és terméknevek változatlanok.

A 0.11.0 Mac Apple Silicon és Windows 11 x64 csomagjai tiszta profillal készülnek. Frissítéskor a meglévő helyi karakterek, tervek, holdak és beállítások megmaradnak.

A Consumption / Fogyasztás nézet az üzemanyagot is árazza: holdanként, Athanor/Metenox bontásban és összesítve. A négy Fuel Block közül választható típus (kezdetben Hydrogen) minden fúróra érvényes. A kézi, legfeljebb négy tizedesjegyes ISK-egységár csak a blokkok piaci árát írja felül; a Magmatic Gas a választott Jita buy/sell/split árral számít. Üres mező = visszatérés a piaci árhoz; nulla kézi ár is megadható. A típus és a felülírás gépenként mentődik. A költség a 720 órás fogyasztást és a külön megadott bekapcsolások blokkjait is tartalmazza. A struktúraszűrő az árazott mennyiségekre is hat.

A PI új **Időalapú termelési becslés** nézete a kolónia `last_update` idejéből indul, és minden megtekintéskor az aktuális időhöz számol. Az HTTP-cache frissülése nem hosszabbítja meg a készletfedezetet. A kitermelőknél a program időtartama, abszolút vége, hátralévő ideje és ciklusszáma látható. A gyárak diszkrét ciklusai fogyasztják a puffer- és raktárkészletet; a kész termékek az ellenőrzött útvonalakon továbbjuthatnak a következő gyárhoz. A már elindult ciklus bemeneteit nem vonjuk le újra. Megjelenik a készletből várható leállás és a pillanatkép óta / a kiválasztott jövőbeli időszakban várható termékmennyiség.

Ez feltételes, új import nélküli előrejelzés. A fő becslés a kitermelőprogram végét és a ciklusonként változó kitermelést is figyelembe veszi a [CCP fejlesztői képletével](https://developers.eveonline.com/docs/guides/pi/): ciklushossz, alaphozam, csökkenés és ingadozás. A 0.012 / 0.8 dogma alapértékeket a 3607705-ös SDE-ben az összes ECU-típusra ellenőriztük. A **Csak tárolt készletből** oszlop külön, jövőbeli kitermelés nélkül mutatja a készletből fedezhető leállást. A program lejárta után új kitermelés nincs, de a meglévő anyagokból a gyárak tovább dolgozhatnak. Az adatideje előtti ciklusokat nem könyveljük jóvá újra. Régi/hiányzó gyári fázisnál a pillanatkép idején feltételezett újraindítást jelezzük. A közös készlet kiszolgálási sorrendje, kimeneti kapacitáskorlát, hibás időbélyeg és a számítási korlát külön jelzést kap. A modell legfeljebb 90 napot és 100 000 eseményt vizsgál; 30 napnál hosszabb jövőbeli fedezetet nem ígér. Az eredeti ESI-pillanatkép és annak készletellenőrzése külön megmarad; a becslést nem írjuk vissza a személyes vagy corp készletbe.

### Ipari költségek, értékesítés és holdprofit

A Struktúrák és bónuszok menüben manufacturinghoz és reakcióhoz külön rendszer választható a holdaknál használt, gépelésre szűkülő rendszerlistából. A system cost index a nyilvános ESI `/industry/systems/` végpontjáról érkezik; az EIV-hez szükséges adjusted price a `/markets/prices/` végpontról. A két adathalmaz külön, tartós cache-t és ETag-et használ, a frissítés a szerver lejáratát betartja. Hibánál a korábbi teljes adathalmaz megmarad, régi adatként jelölve. Hiányzó index vagy adjusted price esetén a teljes job cost nem jelenik meg nullaként.

A [CCP Viridian-képlete](https://www.eveonline.com/news/view/viridian-expansion-notes): `EIV × (SCI × job-cost szorzó + facility tax + SCC + Alpha)`. EIV = az eredeti, anyagbónusz és ME előtti recept mennyiségei × ESI adjusted price, runonként. A job cost kedvezmény csak az SCI-részt csökkenti. A facility tax közvetlenül az EIV-re hat, nem a rendszer díjára. Az SCC manufacturing és reakció alapértéke 4%, a [21.06-os CCP-változás](https://www.eveonline.com/news/view/patch-notes-version-21-06) alapján; a mező szerkeszthető. Az Alpha-pótdíj külön állítható, kezdetben 0%. Az összegek becslések: jobonként és díjösszetevőnként két tizedesre kerekítünk, majd a jobdarabszámmal szorzunk.

A Production material cost panelhez hozzáadódik a hátralévő jobok díja és az anyaggal együttes költség, valamint a terv teljes célmennyiségének bruttó Jita buy és sell eladási értéke. A két eladási ár együtt látható és független az anyagárazás választásától. A meglévő késztermék és WIP miatt a hátralévő költség nem feltétlenül a teljes céltétel történeti bekerülése. A részletes jobtábla az EIV-t, rendszert, indexet és díjösszetevőket is mutatja. Piaci ajánlat hiányában az eladási érték `–` marad.

A holdak Production value at Jita paneljében az üzemanyag, Magmatic Gas, megadott holdbérlet, egyéb havi költség és értékesítési díj összege, valamint a 30 napos profit is megjelenik. A hold szerkesztőjében adható meg a bérlet és az egyéb költség; az utóbbiba tartozhat bányászat, finomítás, külön Tatara-fogyasztás, szállítás vagy amortizáció. Az összeg működési állapottól független fix költség. A Számítási beállításokban megadott eladási adó minden eladásra, a broker fee sell/split módban hat; buy módban nem adunk hozzá új eladási megbízási díjat. A díjak kezdetben 0%-osak, így csak a ténylegesen megadott költségek számítanak. Hiányzó árnál nem állítunk teljes költséget vagy profitot. A struktúraszűrő a bevételt és a költségeket együtt szűri. A Fuel Block kézi árában az ezresek tagoltak, a négy tizedesjegy megmarad.

## Az 1.0.0 holdnaptárának működése

A Folyamatban oldalon külön figyelmeztetés és menüjelzés mutatja az átvehető (`ready`) jobokat. A még `active` állapotú, de időben már lejárt jobot „várhatóan elkészült” jelzéssel mutatjuk; szüneteltetett, átvett vagy törölt job nem kap készjelzést.

A Holdak és kitermelés új **Kitermelési naptár** füle UTC havi naptárat, részleteket és holdankénti figyelmeztetést ad. A karakter naptárát (`esi-calendar.read_calendar_events.v1`) és a corporation kitermelési időzítőit (`esi-industry.read_corporation_mining.v1`) külön engedélyezett, csak olvasó ESI-kérésekkel olvassa. A hozzáférés a Settings → Data access részben adható meg. A Client ID tulajdonosának az EVE Developer alkalmazásban is engedélyeznie kell a naptár, corporation mining és karakterértesítési scope-okat. A corporation szerepkörei továbbra is szükségesek; más corporation bérelt fúrója nem feltétlenül látható. A naptár hallgatásából nem állítjuk, hogy biztosan nincs extraction. A Metenoxnak nincs kézi extraction-időzítője, így nem adunk ilyen figyelmeztetést rá.

Az ESI `natural_decay_time` **automatikus széttörés**, nem az ércek eltűnése. Az ércek eltűnését az érkezés–automatikus széttörés tartományából és a holdnál szerkeszthető élettartamból becsüljük (alapérték 48 óra). A korábbi kézi széttörés, a rig és a játékon belüli eltérés miatt ez nem garantált időpont. [CCP: Moon Mining](https://support.eveonline.com/hc/en-us/articles/115005404229-Moon-Mining), [CCP: Refineries and moon mining](https://www.eveonline.com/de/news/view/the-goo-must-flow-everything-about-refineries-and-moon-mining).

A kitermelési időzítő nem ad ércösszetételt. Ha a holdhoz egyértelműen kapcsolható naptárbejegyzés ércenként explicit m³-adatot tartalmaz, abból számolunk automatikus térfogatarányt. Ezt **ESI naptár · automatikus** forrásjelzéssel, az eredeti kézi adat megőrzésével használjuk. Hiányzó, elavult, ismeretlen vagy ellentmondó adatra nem írunk felül kézi ércarányt. Más esetben a térfogat a kitermelés ESI-időtartama × az ismert órás ütem × a kézi arány, látható becslésjelzéssel. A HTTP-cache és az ETag tiszteletben marad; egy hibás/hiányos frissítés megőrzi az előző teljes pillanatképet. A már látott korábbi események legfeljebb 90 napig maradnak meg; a friss listából eltűnt jövőbeli időzítő nem jelenik meg újra aktívként.

A Bányászkristályok fülön hold és konkrét kitermelés, illetve 30 napos becslés választható. A kristályokat igénylő érceket kategóriánként összevonjuk, és a térfogatarány **legkisebb egész számarányát** adjuk: 75% / 25% → **3 / 1 kristály**. Nincs kopás-, ciklus- vagy hajókihozatal-számítás. Ez arányos készletjavaslat: a számok 1–9 közöttiek; szükség esetén felfelé kerekített közelítő arányt használunk. Metenoxhoz nem kell kristály.

### Ércadatok karakterértesítésekből és pontos hozzáférési állapot

A holdadatok engedélyezése most a `esi-characters.read_notifications.v1` olvasási scope-ot is kéri. A karakternek meg kell kapnia a megfelelő corporation holdértesítéseit; a scope önmagában nem hoz létre hiányzó értesítést. A naptár, corporation időzítő és ércértesítés hozzáférése és frissítési állapota külön sorban látszik. A scope-lista és az általános beállítási súgó alapból csukott technikai részletek közé került. Az újraengedélyezés megtartja a korábbi engedélyeket, automatikusan a holdnézethez tér vissza és frissít. A corporation időzítőknél kapott HTTP 403 a tulajdonos corporationben szükséges **Station Manager** szerepkörre utal; nem jelöljük automatikusan hiányzó EVE-belépésnek.

A `MoonminingExtractionStarted`, `MoonminingExtractionFinished`, `MoonminingLaserFired` és `MoonminingAutomaticFracture` értesítések `oreVolumeByType` mezője az elsődleges mennyiségi forrás. Ércenkénti m³, teljes térfogat, összetételi arány és arányos kristálydarabszám készül belőle, **ESI értesítés · automatikus** jelzéssel. Az időpontok FILETIME- és ISO-formátumát ellenőrizzük. Több karakter azonos eseménye nem többszöröződik; a törlést, elkészülést és széttörést ugyanahhoz a kitermeléshez kapcsoljuk. Megfigyelt széttörésnél a holdhoz beállított élettartam ettől az időponttól számít, továbbra is becslésként.

Az SDE-alapú katalógus 60 tömörítetlen alap-, gazdagabb és jackpot holdércet köt a megfelelő alapkategóriához. A konkrét értesítésben a valódi változat neve és m³-e marad látható; a kristályoknál az azonos kategóriák összeadódnak. A 30 napos alapanyag-előrejelzés továbbra is a dokumentált alapérc-kihozatalt használja: egy megfigyelt jackpotot nem vetítünk ki minden későbbi kitermelésre. A kézi összetétel megmarad. Hibás vagy ismeretlen ércadat nem írja felül automatikusan.

Csak a holdkitermelési értesítéseket tároljuk, más értesítések szövegét nem. Nincs új függőség vagy általános YAML-futtatás; kizárólag a szükséges számmezőket és ércmennyiség-térképet értelmezzük. A HTTP-cache, ETag és a korábbi teljes pillanatkép megőrzése változatlan. Az új scope-ot a Client ID EVE Developer alkalmazásában is engedélyezni kell, majd az érintett karakterrel egyszer újra be kell lépni.

Források: [ESI OpenAPI](https://esi.evetech.net/meta/openapi.json), [goesi notification modellek](https://pkg.go.dev/github.com/antihax/goesi/notification#MoonminingExtractionStarted), [CCP SDE](https://developers.eveonline.com/docs/services/static-data/). A funkciók az 1.0.0 kiadás részei.

## Notification center (native macOS support in 1.1.0)

`muhely/notifications.py` and `/api/notifications` aggregate training, personal/corporation completed jobs, PI stops and upcoming moon extractions (default three days). Training exclusions reuse account tracking; stale, missing and unauthorized data remains review-only. Corporation job identities suppress personal duplicates. Moon scope is inferred from ESI timers or explicitly assigned in Settings; this does not change production inventory scope.

OS delivery is opt-in under Settings → Notifications. The native UserNotifications bridge requests permission only from its explicit button, validates all messages against the exact-origin main-frame boundary, and opens the relevant notification tab/category when clicked. Automatic checks run every four minutes while the application is open, including in the background, through the existing EVE sync/cache paths without changing inventory mode. Closing the app stops monitoring; there is no daemon.

The local SQLite event ledger leases pending events and acknowledges only submissions accepted by macOS. Stable event identities suppress duplicate delivery across refresh/restart; unknown data never resolves an episode. Concurrent alerts are grouped by owner/category. Unit/API/UI tests cover scope isolation, training exclusions, stale guards, PI forecasts, three-day boundaries, settings, lease retry and acknowledgement. The native WebKit smoke test exercises the bridge with synthetic notifications, without granting permission or displaying real system banners.

## Shared operation progress

`static/activity.js` wraps application API requests and tracks concurrent operations independently of the current view. `/api/activity` provides a lightweight authenticated snapshot of background EVE, Jita and industry work without inventory/planning/catalogue locks. `muhely/progress.py` uses a thread-local observer to report stages, character/corporation counters, resources, cached reads and real pagination. Existing requests, atomic commits and cache expiry remain unchanged. Counts are work units, not elapsed-time percentages or invented ETAs. Completion, partial failures and unavailable status polling remain distinct; no release assets are modified.

## Local intel

Intel map monitors selected EVE Chatlogs channels locally, recognizes system/pilot reports and `clr`/`clear`, and offers configurable stargate-jump alerts with explicit ESI, Local-log or manual location provenance. Enable in Settings → Intel settings. See [research and design notes](Intel-reference.md), [Hungarian guide](Hasznalat.md) and [English guide](UserGuide.en.md). Public topology is rebuilt with `tools/build_intel_universe.py` from the official JSONL SDE; private logs and preferences are never bundled.

Intel windows: the complete selected region is shown with shortest-stargate-distance highlighting from the selected own character. Activity cards include exact-ID zKillboard links and CCP ship icons. Public ESI name resolution receives inferred names only, with positive/negative local caching; full chat text stays local. The Mac shell opens separate map and aggregated read-only chat windows sharing cookies/theme/language while keeping OS delivery in the main window. Child windows close independently.


## Native Windows window

The Windows launcher now opens the shared interface in a WinForms/WebView2 window through pinned pywebview/pythonnet dependencies. The portable package includes Python and all Python dependencies; Microsoft WebView2 Runtime and .NET Framework are OS prerequisites. EVE consent opens the system browser and returns to the selected app view. Clipboard, native file save/folder dialogs, print UI, theme/language, independent map/chat windows and opt-in Windows notification-area alerts are supported. The transparent intel overlay also has a native WinForms surface: no title bar or focus theft, click-through in normal use, per-monitor placement, configurable 1–3600-second expiry and immediate suppression when intel notifications are disabled. Borderless windowed EVE is supported; exclusive full-screen and Windows security surfaces may cover the overlay. The Windows CI smoke test exercises its actual HWND, drawing, native styles, expiry and shutdown cleanup.

The bridge uses WebView2 WebMessageReceived/PostWebMessageAsJson directly, checks the exact loopback origin and keeps the existing CSP without unsafe-eval. Remote/file navigation and unapproved child-window actions are blocked; no Python API object is exposed to page scripts. The shell preserves local profiles and DPAPI token storage. `windows_window_smoke.py` exercises the real renderer with a temporary blank profile; `.github/workflows/windows-window.yml` runs that test on Windows using the same pinned embedded runtime and trimmed dependencies as the distributable. A local `Ellenorzes_ablak.cmd` is included. Building on Mac verifies PE/managed architecture, imports, hashes and ZIP integrity; it does not count as a native Windows run.
