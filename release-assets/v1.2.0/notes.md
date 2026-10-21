## Downloads / Letöltés

- **Windows 11 64-bit — native application window / saját alkalmazásablak:** `EVE_Muhely-1.2.0-Windows11-x64.zip`
- **Mac Apple Silicon (M1 or later), macOS 11+ — native application window / saját alkalmazásablak:** `EVE_Muhely-1.2.0-macOS-AppleSilicon.dmg`

## What's new

- Windows now opens in its own WinForms/WebView2 application window, retaining the existing interface, dark/light theme and Hungarian/English UI.
- Native Windows clipboard, file and folder dialogs, printing, separate intel system-map and chat windows, and opt-in Windows notification-area alerts.
- EVE authorization opens the system browser, then returns to the selected application view. Closing checks unsaved edits and running requests.
- Self-contained Python runtime and pinned Windows dependencies. Corrected WebView2 loader search directories without distributing unused ARM/x86 binaries.
- The actual pinned embedded Windows runtime and WebView2 windows passed [Windows-hosted integration tests](https://github.com/Bill-web-eve/eve-workshop/actions/runs/39492249683), covering DPAPI, local API/planning, clipboard, export, authorization return, separate map/chat windows and shutdown. [Application tests also passed](https://github.com/Bill-web-eve/eve-workshop/actions/runs/39492249804).
- The Mac app remains native and is included at the same version. The transparent always-on-top intel overlay remains a Mac-only feature in this release.

## Újdonságok

- A Windows-verzió is saját WinForms/WebView2 ablakban indul, a megszokott felülettel, sötét/világos móddal és magyar/angol nyelvvel.
- Natív Windows-vágólap, fájl- és mappaválasztás, nyomtatás, külön intel-térkép- és chatablakok, külön engedélyezhető Windows-rendszerértesítések.
- Az EVE engedélyezése a rendszerböngészőben történik, majd a kiválasztott alkalmazásnézetbe térsz vissza. Bezáráskor az app figyel a nem mentett módosításokra és a futó lekérésekre.
- Beépített Python és rögzített függőségek; javított WebView2-töltés. A tényleges Windowsos futtatási próba sikeres.
- A Mac Apple Silicon-csomag szintén 1.2.0. Az átlátszó, minden fölött lebegő inteljelző ebben a kiadásban továbbra is Mac-funkció.

## Installation and updating / Telepítés és frissítés

Stop the previous app before replacing it. Windows: extract the complete ZIP and launch **EVE_Muhely.exe**; keep the whole folder together. Microsoft Edge WebView2 Runtime and .NET Framework are required and are normally present on Windows 11. If WebView2 is missing, the app points to [Microsoft's official download page](https://developer.microsoft.com/microsoft-edge/webview2/); it does not silently install system components. Mac: copy the app from the DMG into Applications. Neither platform requires a separate Python, Excel or Codex installation.

Frissítés előtt állítsd le a régi appot. Windowson bontsd ki a teljes ZIP-et, és indítsd az **EVE_Muhely.exe** fájlt; Macen másold az alkalmazást az Applications mappába. A meglévő saját profil megmarad.

Both packages are clean: no characters, saved plans, moons, inventory, account data, chat logs or login tokens. Only the public EVE Client ID is preconfigured. Authorize your own characters under Settings → Data access. Existing profiles are preserved. Mac profiles remain under `~/Library/Application Support/EVE Muhely`; Windows profiles remain under `%LOCALAPPDATA%\EVE Muhely`.

A csomagok személyes adatokat nem tartalmaznak; csak a nyilvános Client ID van előre beállítva. Az új telepítés saját, üres profillal indul, a korábban használt helyi profilokat a frissítés nem törli.

Mac: arm64 only, ad-hoc technical signature, no Apple Developer ID or notarization. Windows: portable x64, no publisher signing. Native Windows tests run on a Windows-hosted CI runner, rather than a physical Windows 11 PC; `Ellenorzes_ablak.cmd` also checks the actual renderer with an isolated temporary profile on the recipient's machine. Installer hashes and archive integrity are verified before publication.
