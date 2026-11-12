# Signed application updates

The native shells use a shared Ed25519 verifier and a detached, copied Python runtime for application replacement. This preserves the existing Mac Cocoa and Windows WebView2 shells and portable packaging. No external update framework, privileged service or EVE token is involved.

## Trust and publishing

- `data/update-public-key.json` is the pinned public trust anchor, copied by both clean package builders. It is independent of `data/defaults.json`, which still contains only the public EVE Client ID.
- The private key is outside the repository in the maintainer's protected local release-key directory. Back it up securely; losing it requires distributing a new trusted application manually. Never upload it as a release asset or commit it.
- Build both normal packages. The Mac builder also emits `EVE_Muhely-VERSION-macOS-AppleSilicon-update.zip`, preserving framework symlinks and executable modes.
- Create the usual release manifest and notes. Run `python tools/sign_release_updates.py --manifest release-assets/vVERSION/manifest.json --key-file PATH_TO_PRIVATE_KEY`. The tool verifies the local key matches the embedded public key, creates `update.json`, and adds the descriptor and Mac update ZIP to the asset manifest.
- `python tools/publish_github_release.py --all --check` validates archive hashes and signatures. Updater-enabled releases from 1.9.0 onward cannot be published by this tool without signed update metadata. Historical releases remain valid without it.
- GitHub Actions verifies all files before publication; no private signing key is needed on GitHub. The descriptor becomes discoverable through the public latest stable release's `/releases/latest/download/update.json` URL. Drafts/prereleases are not update channels.

The signed payload includes the exact stable version, fixed-repository release-notes URL, platform, filename, download URL, compressed size and SHA-256. The signature covers a canonical JSON representation. No public key supplied by a feed is accepted. All URLs and filenames must match the expected repository, tag and platform naming convention; arbitrary commands and UI-supplied install paths are not supported. A previously cached newer descriptor is never replaced by an older one.

## Installation boundaries

A CSRF-protected download endpoint prepares an opaque one-day ticket. Only the main native window can hand that ticket to the installer. The installer derives the target from its own packaged executable, copies its runtime away from the target (important for Windows DLL locks), and starts a detached helper. The main app uses its existing complete shutdown path.

The helper repeats signature/hash validation, rejects archive traversal, aliases, device nodes and symlink-parent writes, permits only internal Mac framework symlinks, validates the payload version, and waits for the exact main/service PIDs without killing them. It backs up SQLite, stages the new app on the installation filesystem, and retains the previous copy. A failed swap restores the original directory. It restarts the app and verifies the version on the loopback health endpoint. A startup failure is recorded and both app copies and the pre-update database backup remain available; automatic database rollback is intentionally avoided.

Files used by the updater live in the profile's `updates` directory. Database backups live in `backups`. Failed update status appears in Settings → Updates; detailed helper diagnostics are in `updates/TICKET/install.log`. Old application copies are retained beside the installation; they can be removed manually after confirming the new version works. Automatic updates download/install only on an explicit user action. The daily automatic operation only checks metadata.

Source/developer launches and read-only installations require manual installation. The first updater-enabled release must be installed manually, since released 1.8.0 clients do not contain an updater. This feature commit does not publish a new version or overwrite the already installed development Mac app.

## Checks

Python tests cover signature/tampering, exact asset validation, cache/rate policy, corruption, traversal and symlink cases, database backup and failed-swap recovery. UI tests cover the single-click download/verified-install path, pending edits/tasks, native-only access, progress, errors and shutdown. The Mac shell is compiled separately. The Windows hosted check additionally runs `windows_update_smoke.py`: an ephemeral test signing key, copied embedded runtimes, two real process exits, directory replacement, synthetic launcher restart/health handshake and profile/backup verification. It never uses the maintainer's signing key or a user's installed application.
