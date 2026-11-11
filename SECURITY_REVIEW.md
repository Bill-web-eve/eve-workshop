# CodeQL review — 2026-11-11

Scope: the 27 open `main` alerts visible in GitHub Code scanning during this review. The public CodeQL API requires authentication, so the authenticated GitHub UI was used to read the alert list and reported locations. No alerts were dismissed and no scanner rules were disabled. A fresh CodeQL analysis is required to confirm which alerts close after these changes.

## HTML/text boundaries: 20 reported paths

Alerts **4–13, 15–19, 21–23, 25–26** (excluding IDs absent from the open list) concern DOM text or exception text reaching HTML rendering in `static/app.js`, `static/fleet.js`, `static/intel.js` and attribute translation in `static/i18n.js`.

- The shared encoder already escaped `&`, `<`, `>`, quotes and apostrophes through a replacement table. It now uses explicit ordered replacements, preserving the output while making the text-to-HTML boundary easier to audit and analyze. Ampersands are encoded first, so pre-encoded entities remain literal text.
- Renderers append new markup with `insertAdjacentHTML('beforeend', …)` rather than `innerHTML += …`. Existing DOM markup is no longer read and reparsed during each append, and previously created nodes and listeners are preserved.
- Translations only write to the four explicitly named text attributes (`title`, `aria-label`, `placeholder`, `alt`). There is no dynamic destination attribute that could become a URL, style or event handler.
- Regression checks supply HTML tags, event attributes, quotes, ampersands and exception messages. They verify literal text, unchanged attribute values, absence of injected elements/handlers, translation reversal and normal page behavior.

These findings are related paths, not twenty independently demonstrated exploits. The previous shared encoder already protected these values; the changes strengthen and clarify the boundaries rather than asserting that the old app executed injected scripts.

## Response headers: alert 3

The reported Content-Type originated from MIME inference for an already allowlisted static request. Static content types now come exclusively from a server-owned constant map. Every caller-supplied response header is validated before any status line or header is written: invalid names, CR/LF, other control characters and non-Latin-1 header values fail before output starts. Calendar downloads and percent-encoded redirects retain their existing behavior.

Tests poison the OS MIME inference function, exercise the actual static routes, try encoded request-path injection and verify invalid header values cannot write even a partial response.

## URL assertions: alerts 1–2 and 27–29

Alerts **1–2** refer to release/self-test diagnostics, not the production JWT verifier. Those diagnostics now compare the EVE SSO issuer against the two exact HTTPS root issuer values; prefix lookalikes, credentials, extra paths, other schemes and ports fail. Production JWT verification already used an explicit issuer allowlist and was not changed.

Alerts **27–29** refer to negative assertions in intel UI tests: the assertions check that raw dscan URLs are not displayed, rather than validating a navigation destination. They now assert that no HTTP(S) URL appears in those text fields. Production dscan hostname validation remains unchanged, and the existing hostile-host and JavaScript-URL tests continue to run.

## User-selected Boost directory: alert 14

This is a deliberately user-controlled local directory, not an untrusted filename joined to a privileged server root. The application must support EVE chat logs outside its profile, including manually selected/custom locations.

Relevant boundaries:

- `/api/boosts/channels` requires the local application's session and valid Host. Starting/stopping the counter requires the authenticated same-origin/CSRF-protected POST routes.
- Directory selection now requires an existing absolute directory after home expansion and rejects control characters. Invalid or inaccessible paths produce the normal user-facing folder error.
- Discovery only lists matching Boost chat-log basenames, without opening file contents or recursively scanning directories.
- Reads use only matching entries from the selected directory, reject symlinks, open with `O_NOFOLLOW` where supported, verify regular files and require the expected channel/Listener header. Existing tests cover wrong headers and symlinked files.
- The app runs under the user's OS permissions; it is not a privileged file service and does not claim to sandbox the user's own folder choices to its application profile.

A scanner may still report this intentional directory probe as `py/path-injection`. That remaining report needs a design-aware false-positive review; it should not be hidden by moving input through storage, disabling the query or breaking arbitrary local log-folder selection. No dismissal was performed as part of this change.

## Follow-up after the first verification scan

The CodeQL run for `520f08c` completed successfully, but the alert list was not clean: it showed 36 open and 24 closed reports. Several changed HTML sink locations were reported under new alert numbers. The review therefore continued instead of treating a successful scanner execution as a clean result.

One inspected path ran from a DOM label through the shared translation cache and table markup into an HTML insertion. The follow-up uses conventional regular-expression replacements in all five HTML encoders (app, tables, activity, manual and location labels), explicitly encodes translated labels interpolated into markup, and uses the unambiguous `textContent` setter for text-node translation. Translation data remains unencoded when used as plain text or stored form data; encoding happens only at the HTML boundary. The readiness fallback label is also encoded without changing its intentional location markup.

Additional tests substitute HTML-like translated labels and hostile table headings, alongside the existing literal-text and exception-message tests. These checks verify behavior; another fresh CodeQL analysis is still required to validate the report list. The intentional local Boost-directory selection remains a separate design-aware review item.
