# Kész csomagok közzététele

A jelenlegi kiadás **0.11.0**, Mac Apple Silicon és Windows 11 x64 csomaggal, magyar–angol felülettel, Jita-árazással, ipari díjakkal, holdprofit- és PI-előrejelzéssel. A `v0.11.0/manifest.json` felsorolja a hat ellenőrzött mellékletet és SHA-256 összegüket.

A helyi kiadási commit elkészítése után a GitHub Desktopban a **Push origin** indítja a feltöltést. A main ágra érkezett kiadási változás elindítja a **Mac es Windows csomagok kozzetetele** munkafolyamatot. Siker után a csomagok itt tölthetők le: https://github.com/Bill-web-eve/eve-workshop/releases.

A folyamat először piszkozatot készít, ellenőrzi és feltölti a csomagokat, majd publikál. Megszakadt futás folytatható. Egy már publikált, módosítható kiadásból hiányzó mellékleteket is pótol, de eltérő meglévő fájlt nem ír felül és immutable kiadást nem módosít. Személyes tokenre nincs szükség: a munkafolyamat csak az adott repositoryhoz kap ideiglenes GitHub-tokent.

Helyi ellenőrzés: `python3 tools/publish_github_release.py --all --check`. A helyi commit még nem jelent GitHub-közzétételt; a Push origin és a GitHub Actions sikeres futása szükséges.

Az ellenőrzött telepítők a repositoryban is tárolódnak, így növelik a klón méretét. A korábbi `v0.8.1` csomagjai megmaradnak. Később a fordításból közvetlenül feltölthető kiadásokkal ez a megoldás kiváltható.
