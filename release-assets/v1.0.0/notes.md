## Letöltés / Downloads

- **Mac Apple Silicon (M1 vagy újabb), macOS 11+:** `EVE_Muhely-1.0.0-macOS-AppleSilicon.dmg`
- **Windows 11 64-bit:** `EVE_Muhely-1.0.0-Windows11-x64.zip`

## EVE Workshop 1.0.0

Az 1.0.0 az eddigi fejlesztések közös Mac- és Windows-kiadása, teljes magyar és angol felülettel.

- Gyártási és reakcióláncok, nettó alapanyaghiány, BPO/BPC ME/TE, példányszám és runkezelés, személyes és corporation készletek szigorú elkülönítése.
- Mentett tervek készlet-, aktív jobkimenet- és BPC-run-foglalással; összesített anyaghiány. EVE Multibuy másolás blueprintek nélkül.
- **Production scheduler:** karakterenkénti aktív skillek, külön manufacturing/reaction slotkeret, egyedi blueprintek, anyagfüggőségek és érkezési idők. Csak meglévő BPO/BPC-k vagy további beszerzést is megengedő mód, hiányzó példányok és runok külön jelölve.
- **Schedule graph and timeline:** karakterszűrő, állítható látható napok (alapból 7), időszaklapozás, teljes időtáv és részletes anyagforrások. Minimum jobhossz alapból 12 óra, szerkeszthető; a jobok között nincs kötelező várakozás. Biztonságosan összevont egymást követő reakciók, fölösleges többletgyártás nélkül.
- **Moon management:** kézi holdnyilvántartás, rendszerkereső és constellation, Athanor/Metenox termelés, fogyasztás és profit. ESI kitermelési naptár, karakterértesítésből származó ércadatok, adatforrás-jelölések, hiányzó kitermelési adatok figyelmeztetése, helyi naptárfeliratkozás és ICS-export.
- Holdanként választható bányászkristály-terv: térfogatarányok alapján 1–9 közötti egész arányok; kopás számítása nélkül.
- **Accountok és tanulás:** kézi accountcsoportok, Omega/MCT-lejáratok és tanulási helyek. A tanulásra nem jogosult karakterek nem kapnak indokolatlan üres-sor riasztást. Az ESI nem szolgáltat előfizetési lejáratot vagy accountazonosítót.
- Közös **Settings** menü struktúrákkal és bónuszokkal, kapcsolattal, adathozzáférésekkel, holdszámításokkal, naptárszinkronnal és accountokkal. A kész industry jobok külön figyelmeztetést kapnak.
- Jita buy/sell/split anyagárak, késztermék-eladási érték, ESI system cost index, szerkeszthető facility tax és ipari díjak. Holdak 30 napos bevétele, üzemanyag-, bérleti, egyéb és eladási költsége, valamint profitja. PI-előrejelzések a kolóniapillanatkép időpontjától.
- **Documentation:** teljes magyar és angol kézikönyv, kereséssel, tartalomjegyzékkel, letöltéssel, nyomtatás/PDF lehetőséggel. Sötét/világos mód, rendezhető és becsukható szűrősorú táblázatok, egyszerű szöveges itemnév-másolás.

## What's new

Version 1.0.0 brings the development changes together in clean Mac and Windows distributions.

- Manufacturing and reaction chains, net material shortages, owned BPO/BPC parameters and run capacity, separate personal/corporation inventories, saved-plan stock/WIP/BPC reservations and combined EVE Multibuy purchasing.
- **Production scheduler** with verified active skills, separate reaction/manufacturing slots, physical blueprints, input availability and dependencies. Choose owned blueprints only or allow additional procurement, with explicit blueprint shortages.
- **Schedule graph and timeline** with character filtering, adjustable visible days (default 7), previous/next periods, full time range and input-source details. Configurable minimum job duration (default 12 hours), without mandatory gaps or extra production merely to fill the minimum.
- **Moon management** with register, Athanor/Metenox output, fuel and profitability, ESI extraction calendar, notification-derived ore quantities and source labels, missing-data warnings, local calendar subscriptions and ICS export. Per-moon crystal suggestions use approximate 1–9 ratios, without wear calculations.
- Manual account grouping, Omega/MCT expiry tracking and training-place assignments; unavailable training places do not cause false idle warnings. ESI does not provide account identity or subscription expiry.
- Consolidated Settings, completed-industry-job warnings, Jita pricing and sales values, industry fee estimates, moon profit and snapshot-based PI forecasts.
- Complete **Hungarian and English documentation** inside the app, with search, contents, download and print/PDF. Dark/light themes, sortable/filterable tables and plain-text item-name copying.

## Telepítés és frissítés / Installation and updating

Macen másold az alkalmazást az Applications mappába; Windowson bontsd ki a teljes ZIP-et, majd indítsd az **EVE_Muhely.exe** fájlt. A teljes Windows-mappát tartsd együtt. Python, Excel és Codex telepítése nem szükséges.

Frissítés előtt állítsd le a régi alkalmazást az oldalsáv alján. A külön tárolt helyi profil megmarad: karakterek, tervek, foglalások, holdak és beállítások nem törlődnek. Az új kiadás csomagja tiszta: nincs benne karakter, mentett terv, hold, készlet vagy belépési token; csak a nyilvános EVE Client ID előre beállított. Minden felhasználó a saját karaktereit engedélyezi. Cím: **http://127.0.0.1:8765**. Telepítés után frissítsd az oldalt és számold újra az ütemtervet. Új ESI-funkcióhoz a szükséges scope-okat is engedélyezni kell.

On Mac, copy the app to Applications. On Windows, extract the whole ZIP and run **EVE_Muhely.exe**, keeping the full folder together. No separate Python, Excel or Codex installation is needed. Stop the previous app before replacing it. Existing local profiles are preserved. Packages contain no characters, plans, moons, stock or login tokens; only the public Client ID is preconfigured. Authorize your own characters. The browser address is **http://127.0.0.1:8765**. Reload the page and recalculate schedules after updating. Newly used ESI features require their respective permissions.

## Ellenőrzés és korlátok / Verification and limits

- A csomagokhoz SHA-256 ellenőrzőösszeg és telepítési útmutató tartozik. / SHA-256 checksums and installation instructions are included.
- Mac: csak ARM64; nincs Developer ID és notarizáció. A kötelező helyi technikai aláírás megmarad. / ARM64 only; ad-hoc signing, without Developer ID or notarization.
- Windows: portable AMD64 csomag, ellenőrzött binárisarchitektúrával, DLL-függőségekkel és ZIP-integritással. Ezen a Macen natív Windows 11 futtatási próba nem történt; az **Ellenorzes.cmd** külön tesztprofilt használ. / Native Windows execution remains unverified on this Mac; the included smoke test uses an isolated profile.
- Az ütemező becslést készít és nem indít EVE-jobot. Az árak, díjak, PI-hozam és érceltűnés becslések; hiányzó adat nem számít nullának. / Scheduling is a heuristic and never launches EVE jobs. Prices, fees, PI output and belt expiry are estimates; missing data is not treated as zero.
