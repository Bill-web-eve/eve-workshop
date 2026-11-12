# Kész csomagok közzététele

A legújabb előkészített kiadás **1.8.0**, saját ablakos Mac Apple Silicon és Windows 11 x64 csomaggal. Újdonságok: eve-preview mindkét platformon, beállítható gyorsbillentyűk, bányászati és sebzésjelzések, Research agentek, intel- és biztonsági javítások. A `v1.8.0/manifest.json` a hat ellenőrzött mellékletet és SHA-256 összegüket tartalmazza.

A helyi kiadási commit feltöltése a GitHub Desktop **Push origin** gombjával elindítja a **Mac es Windows csomagok kozzetetele** munkafolyamatot. Csak a teljes alkalmazásteszt és a valódi Windows WebView2/overlay/preview automatizált próba sikere után publikál. A preview tesztje saját tesztablakokat használ; valódi EVE-klienssel végzett Windows-próba még nem történt.

Letöltések sikeres publikálás után: https://github.com/Bill-web-eve/eve-workshop/releases.

A folyamat a korábbi kiadások mellékleteit is ellenőrzi. Meglévő fájlt nem ír felül; eltérő tartalomnál leáll. Megszakadt feltöltés újraindítható. A GitHub csak az adott repositoryhoz ad ideiglenes közzétételi tokent; személyes token nem kell.

Helyi csomagellenőrzés: `python3 tools/publish_github_release.py --all --check`. A helyi commit még nem jelent közzétételt: feltöltés és sikeres GitHub Actions-futás szükséges.

A telepítők üres profillal, kizárólag a nyilvános EVE Client ID-val készülnek. A már meglévő helyi felhasználói adatokat a frissítés megőrzi.
