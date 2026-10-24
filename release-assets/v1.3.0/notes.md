## Downloads / Letöltés

- **Windows 11 64-bit — native application window / saját alkalmazásablak:** `EVE_Muhely-1.3.0-Windows11-x64.zip`
- **Mac Apple Silicon (M1 or later), macOS 11+ — native application window / saját alkalmazásablak:** `EVE_Muhely-1.3.0-macOS-AppleSilicon.dmg`

## What's new

- Character kills and losses, fleet sessions, observed ESI locations and routes, per-system battle windows and ISK totals. Sessions include at least 15 minutes before the first kill and after the last one.
- Editable battle reports with two to four sides inferred from combat relationships. Alliance/corporation groups can move between sides. Losses are summarized by ship type, with counts, ship icons and total values; killmail icons open zKillboard.
- A resumable live zKillboard feed for character activity and regional kill intel. Nearby arrivals in the same system are grouped on the map and in alerts. Notifications show systems and ships, without ISK values.
- Separate intel notification controls, compact map callouts and region selectors that remain usable during background updates. The transparent intel overlay remains Mac-only.
- Search across all personal or corporation items independently of the current production plan. In progress can show all personal characters together.
- Per-corporation monitoring switches and a minimum 15-minute automatic ESI polling interval, with explicit manual refresh and separately enabled position tracking as exceptions.
- Improved PI extractor timing and planet-local factory stock forecasts. Moon calendar matching and optional-source permission messages have also been improved.
- Updated English and Hungarian user guides. Both packages use their own native application windows and bundled Python runtimes.

## Újdonságok

- Karakterenkénti kill- és lossnapló, flottamenetek, megfigyelt ESI-pozíciók és útvonalak, rendszerenkénti harci időablakok és ISK-összesítések. A jelentések legalább 15 percet hozzáadnak az első kill elé és az utolsó után.
- Kettő–négy szerkeszthető harci oldal, a harci kapcsolatokból becsült besorolással. Az alliance/corporation csoportok oldalak között mozgathatók. Hajótípusonként összesített veszteségek és hajóikonról nyitható killmailek.
- Folytatható élő zKillboard-adatfolyam és csoportosított régiós killjelzések a térképen, illetve az értesítésekben. Az értesítés a rendszert és a hajókat mutatja, ISK-érték nélkül.
- Külön kapcsolható intelértesítések, kompakt térképes kártyák és háttérfrissítés közben is használható régióválasztó. Az átlátszó inteloverlay továbbra is csak Macen érhető el.
- Tervtől független személyes és corporation itemkereső; minden személyes karakter folyamatban lévő munkája egy nézetben is megjeleníthető.
- Corporationönként kikapcsolható adatfigyelés és legalább 15 perces automatikus ESI-lekérés. A kifejezett kézi frissítés és az engedélyezett pozíciókövetés külön szabály szerint működik.
- Javított PI-kitermelési időzítők, bolygónkénti gyári készletbecslés, holdnaptár-egyeztetés és a hiányzó opcionális engedélyek jelzései.
- Frissített magyar és angol kézikönyv, saját ablakos Mac- és Windows-alkalmazás, beépített futtatókörnyezettel.

## Installation and updating / Telepítés és frissítés

Stop the previous app before replacing it. Windows: extract the complete ZIP and launch **EVE_Muhely.exe**; keep the whole folder together. Microsoft Edge WebView2 Runtime and .NET Framework are required and are normally present on Windows 11. Mac: copy the app from the DMG into Applications. Neither platform requires a separate Python, Excel or Codex installation.

Frissítés előtt állítsd le a régi appot. Windowson bontsd ki a teljes ZIP-et, és indítsd az **EVE_Muhely.exe** fájlt; Macen másold az alkalmazást az Applications mappába. A meglévő saját profil és beállítások megmaradnak.

The packages contain no characters, saved plans, inventories, login tokens or Client Secret. Only the public EVE Client ID and public game catalogue are preconfigured. The Mac package has mandatory local ad-hoc signing, without Developer ID or notarization; the Windows package has no publisher certificate. Operating-system protection settings are not changed.

A csomagokban nincs karakter, mentett terv, személyes készlet, belépési token vagy Client Secret. Csak a nyilvános EVE Client ID és a nyilvános játékkatalógus van előre megadva. A kiadások fejlesztői/kiadói tanúsítvány nélkül készülnek.

Publication is gated by an isolated Windows test of the pinned embedded x64 runtime and real WebView2 windows. The Mac frozen backend, disk image and package contents are checked locally. SHA-256 checksum files and installation instructions are included with both downloads.
