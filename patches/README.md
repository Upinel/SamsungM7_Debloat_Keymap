# M7 patches for Vetro 0.3.5

These changes are what make Vetro behave correctly on the M7
(`LS32BM701UUXXU`, Tizen 6.5, `T-NKLBWWC-1720.7`, BT-S).

Vetro is MIT-licensed. The patched binary and source diff are redistributed
under the same license; see `../NOTICE.md`.

## Patched dock binary

`tvlauncher-dotnet-m7.dll`

```text
sha256 bdb12475da8c77700f1c563f85cd7bca50f08cca51a81ddcfa6091780602ed7b
built from Vetro 0.3.5, source revision fb1cadc66ff52cd86358b751e17c1cfb225e0733
```

Install path on TV:

```text
/opt/usr/apps/vetrotvapp/res/wgt/native/dock/tvlauncher-dotnet.dll
```

It fixes the Home-key **release** closing the dock. The TV focuses the dock on
the Home press and then delivers `XF86Home` again on release; without the fix the
dock opens and instantly hides. Source diff: `Program.cs.patch`.

Rebuild from Vetro source:

```bash
git clone https://github.com/andrearicci93/vetro
cd vetro
git checkout fb1cadc66ff52cd86358b751e17c1cfb225e0733
git apply /path/to/Program.cs.patch
cd dock
dotnet build -c Release Launcher.csproj
# output: bin/Release/netcoreapp3.1/tvlauncher-dotnet.dll
```

## Service patches

Applied by `../scripts/apply-m7-patches.py`. Each original file gets a `.m7bak`
backup on the TV.

### `service/control.js`

Adds the native source keysyms and aliases:

```js
'XF86DiscretHDMI1', 'XF86DiscretHDMI2', 'XF86DiscretHDMI3',
LAN_KEYS.KEY_HDMI1 = 'XF86DiscretHDMI1';
LAN_KEYS.KEY_HDMI2 = 'XF86DiscretHDMI2';
LAN_KEYS.KEY_USBC  = 'XF86DiscretHDMI3';
```

Vetro's remapper only accepts `KEY_*` action names. The aliases let those
actions resolve to the TV's native `XF86DiscretHDMI*` keys.

### `service/dock.js`

Removes `--kill-on-home com.samsung.tv.csfs` from the dock's start command.
On the M7 that guard killed Samsung Home when the Samsung Home pill was used.

### `service/dock-catalog.js`

Changes the Samsung Home row from:

```text
samsunghome  Samsung Home  sys:com.samsung.tv.csfs
```

to:

```text
samsunghome  Samsung Home  key:XF86Home  com.samsung.tv.csfs
```

`sys:` starts the Home process but does not bring it to the foreground on this
firmware; injecting `XF86Home` does.

### `service/main.js`

Adds a boot watchdog. Vetro's root agent can connect before Wayland/EFL is
ready, and a dock started too early can exit silently. The watchdog retries at
30 s and 90 s.

## Other files

- `inputs.tsv` — TV / HDMI 1 / HDMI 2 / USB-C (`source:41`)
- `remap-rules.json` — physical 226/626/221 to `KEY_HDMI1`/`KEY_HDMI2`/`KEY_USBC`
