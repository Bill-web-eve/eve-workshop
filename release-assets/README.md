# Kész csomagok közzététele

A legújabb előkészített kiadás **1.9.0**, saját ablakos Mac Apple Silicon és Windows 11 x64 csomaggal, alkalmazáson belüli frissítéssel. A `v1.9.0/manifest.json` nyolc ellenőrzött mellékletet és SHA-256 összegüket tartalmazza, köztük az Ed25519-aláírással hitelesített `update.json` fájlt és a külön Mac-frissítési ZIP-et.

Az 1.8.0 vagy korábbi verzióról az 1.9.0-t egyszer kézzel kell telepíteni. Ezután a későbbi stabil kiadások a Beállítások → Frissítések oldalon telepíthetők. A DMG és Windows ZIP a kézi telepítésre szolgál; a Mac `-update.zip` csomagját az alkalmazás frissítője használja.

A helyi kiadási commit feltöltése a GitHub Desktop **Push origin** gombjával elindítja a **Mac es Windows csomagok kozzetetele** munkafolyamatot. Csak a teljes alkalmazásteszt és a Windows WebView2/overlay/preview/frissítési próba sikere után publikál. A próbák saját tesztablakokat és elkülönített profilt használnak.

Letöltések sikeres publikálás után: https://github.com/Bill-web-eve/eve-workshop/releases.

A folyamat a korábbi kiadások mellékleteit is ellenőrzi. Meglévő fájlt nem ír felül; eltérő tartalomnál leáll. Megszakadt feltöltés újraindítható. A GitHub csak az adott repositoryhoz ad ideiglenes közzétételi tokent. A privát frissítési aláírókulcs helyben marad; nincs benne a repóban, a csomagokban vagy a GitHub-tokenben.

Helyi csomagellenőrzés: `python3 tools/publish_github_release.py --all --check`. Aláírási útmutató: [UPDATING.md](../UPDATING.md). A helyi commit még nem jelent közzétételt: feltöltés és sikeres GitHub Actions-futás szükséges.

A telepítők üres profillal, kizárólag a nyilvános EVE Client ID-val készülnek. A korábban meglévő helyi felhasználói adatokat a frissítés megőrzi.
