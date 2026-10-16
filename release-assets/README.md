# Kész alkalmazáscsomagok közzététele

Az első kiadásnál a már elkészült Mac- és Windows-csomagokat ebben a mappában tároljuk, hogy a GitHub Desktop egyetlen push műveletével átadhatók legyenek a GitHubnak. A csomagok Gitben maradnak, ezért a repository első klónozásának méretét is növelik. A későbbi, rendszeresen fordított kiadásoknál érdemes közvetlenül a fordító munkafolyamatból feltölteni a fájlokat.

A `v0.8.1/manifest.json` kizárólag a hat jóváhagyott melléklet nevét és SHA-256 ellenőrzőösszegét tartalmazza. A DMG és ZIP a már ellenőrzött, személyes adatok nélküli csomagok változatlan másolata. A csomagok verziója: Mac 0.8.0, Windows 0.8.1.

## Közzététel GitHub Desktopból

1. Válaszd ki az `eve-workshop` repositoryt.
2. Kattints a **Push origin** gombra; a kiadási commit már elkészült.
3. A `main` ágra érkezett commit automatikusan elindítja a **Mac es Windows csomagok kozzetetele** GitHub Actions-munkafolyamatot, ha a repositoryban a GitHub Actions engedélyezett.
4. Sikeres futás után a telepítők a https://github.com/Bill-web-eve/eve-workshop/releases oldalon tölthetők le.

A munkafolyamat a GitHub által az adott futáshoz biztosított tokennel dolgozik. Nem szükséges új személyes token, jelszó vagy helyi böngészős bejelentkezés. Csak ennek a repositorynak a tartalmához kap írási jogot; külső pull requestek nem indítják el a közzétételt.

Ha a korábbi hibás feltöltés miatt a kiadás már nyilvános, de üres, a javított munkafolyamat ugyanahhoz a kiadáshoz hozzáadja a hiányzó mellékleteket. Nem kell törölni a kiadást vagy visszaállítani piszkozatra. A leírásban szereplő telepítőneveket kattintható letöltési linkekké alakítja, és megőrzi az egyéb hozzáadott szöveget. Lezárt, immutable kiadást nem módosít.

Átmenetileg a repositoryból közvetlenül is letölthetők a csomagok:

- [Mac Apple Silicon 0.8.0](https://raw.githubusercontent.com/Bill-web-eve/eve-workshop/main/release-assets/v0.8.1/EVE_Muhely-0.8.0-macOS-AppleSilicon.dmg)
- [Windows 11 x64 0.8.1](https://raw.githubusercontent.com/Bill-web-eve/eve-workshop/main/release-assets/v0.8.1/EVE_Muhely-0.8.1-Windows11-x64.zip)

A fájlok feltöltése és ellenőrzése először egy piszkozatban történik. A piszkozat csak az összes melléklet ellenőrzése után válik nyilvánossá. Megszakadt feltöltés után a munkafolyamat újraindítható; meglévő eltérő fájlt nem ír felül. Egy már közzétett, azonos tartalmú kiadás újraindításkor változatlan marad.

Helyi ellenőrzés hitelesítés és hálózat nélkül: `python3 tools/publish_github_release.py --check`.

A GitHubra feltöltés megtörténtét és a GitHub Actions sikeres lefutását külön kell ellenőrizni. A helyi commit önmagában még nem teszi elérhetővé a letöltéseket.
