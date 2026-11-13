# Kész csomagok közzététele

A legújabb előkészített kiadás **1.9.1**, saját ablakos Mac Apple Silicon és Windows 11 x64 csomaggal. A Windows-preview pozíciómentési hibáját javítja, és mindkét platformon 100 pixelre csökkenti a minimumszélességet. A `v1.9.1/manifest.json` nyolc ellenőrzött mellékletet tartalmaz, köztük a saját Ed25519-kulccsal aláírt `update.json` fájlt és a Mac-frissítési ZIP-et.

**Frissítés:** az 1.9.0-ból a Beállítások → Frissítések oldalon indítható. Az 1.8.0 vagy korábbi verziókról egyszer kézzel kell telepíteni. A DMG és Windows ZIP kézi telepítő; a Mac `-update.zip` csomagját az alkalmazás frissítője használja. A felhasználói adatok külön mappája megmarad.

A kiadási commit feltöltése a GitHub Desktop **Push origin** gombjával indítja a **Mac es Windows csomagok kozzetetele** folyamatot. Csak a teljes alkalmazásteszt és a natív Windows-próba sikere után publikál. A korábbi kiadások mellékleteit is ellenőrzi; meglévő fájlt nem ír felül, eltérésnél leáll. Megszakadt feltöltés újraindítható.

Letöltések sikeres publikálás után: https://github.com/Bill-web-eve/eve-workshop/releases.

Helyi ellenőrzés: `python3 tools/publish_github_release.py --all --check`. Aláírási útmutató: [UPDATING.md](../UPDATING.md). A privát aláírókulcs helyben marad, nem kerül a repóba vagy a csomagokba. A telepítők nem tartalmaznak karaktereket, terveket, készletet vagy belépési adatokat; csak a nyilvános EVE Client ID és frissítési ellenőrzőkulcs van előkészítve.
