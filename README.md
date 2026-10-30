# Samsung M7 Debloat and Quick INPUT Switch

> Quick remote INPUT switch (remap) HDMI 1, HDMI 2 and USB-C. System
> optimisation and tweaks.

Remap the Netflix, Disney+ and Prime Video buttons to **HDMI 1**, **HDMI 2**
and **USB-C**, with a fast native launcher on the Home key and optional system
debloating.

Tested target:

| | |
|---|---|
| TV | Samsung 32" Smart Monitor M7 |
| Model | `LS32BM701UUXXU` |
| Platform | `22_NIKEL_SMT`, Tizen 6.5 |
| Software | `T-NKLBWWC-1720.7` |
| BT version | `- S` |
| Launcher | Vetro `0.3.5` |
| Installer | Apps2Samsung CLI `3.1.0` |

The same steps should work on closely related NIKEL M7/M8 sets, but the patches
in `patches/` are specific to this firmware family.

---

## What you get

- **Home key → Vetro glass dock**, not Samsung's ad-filled Home.
- **Samsung Home is still one press away** through the dock's Samsung Home pill.
- **Up on the dock → Inputs**: TV, HDMI 1, HDMI 2, USB-C.
- **Netflix button → HDMI 1**
- **Disney+ button → HDMI 2**
- **Prime Video button → USB-C**
- **Root comes back at every boot** without a PC. Vetro's signed service starts
  its root agent through the TV's own SDB at `127.0.0.1`.
- **Optional debloat** through Vetro's dashboard: app flags, component control,
  DNS filtering, HbbTV, and other TV tweaks.

No per-boot script and no Mac needed after setup.

---

## How it works

There are two independent input paths:

1. **Dock input tiles** use Samsung's `org.tizen.tv-viewer` app-control request
   with source numbers:
   - HDMI 1 = `13`
   - HDMI 2 = `14`
   - USB-C = `41`

2. **Remapped app buttons** use the TV's native remote keys:
   - `XF86DiscretHDMI1`
   - `XF86DiscretHDMI2`
   - `XF86DiscretHDMI3` (the TV maps this to USB-C)

Vetro's remapper normally only accepts `KEY_*` names, so the M7 patch adds
`KEY_HDMI1`, `KEY_HDMI2` and `KEY_USBC` aliases for those three native keys.

Vetro's root integration is what makes the remapper persistent: the service and
UID-0 agent are restored on boot through the TV-local SDB, and the saved input
filter reconnects automatically.

---

## Let an AI agent do it

You can hand the job to a capable coding agent. Send it:

- this repository: <https://github.com/Upinel/SamsungM7_Debloat_Keymap>
- the TV's IP address (`TV_IP`)
- the computer's LAN IP (`HOST_IP`)
- the TV model and software: `LS32BM701UUXXU`, `T-NKLBWWC-1720.7`, BT-S
- confirmation that it may root the TV, and that you have physical access to
  accept pairing prompts and confirm dialogs

A suitable prompt:

> Read the README and `docs/AI-AGENT.md` in
> https://github.com/Upinel/SamsungM7_Debloat_Keymap and set up Vetro plus the
> HDMI 1 / HDMI 2 / USB-C button remap on my Samsung M7. TV IP is `<TV_IP>`,
> computer IP is `<HOST_IP>`. The model is `LS32BM701UUXXU`, software is
> `T-NKLBWWC-1720.7`, BT-S. I accept the root risk and can press buttons on the
> TV when asked. Verify with `scripts/verify.py` and test after a cold boot.

The agent should use the scripts rather than inventing new commands, and should
stop and ask you when the TV screen or UI focus is unclear.

### A note about Claude and other hosted assistants

Some assistants, **including Claude**, may decline requests that describe
rooting, exploitation, or low-level device modification, even when the device
is yours and the goal is a personal launcher or input remap. This is a safety
policy refusal, not a technical limitation of this guide.

If that happens:

- use a different coding agent or a local agent without that restriction;
- run the steps yourself using this README; or
- ask the agent to assist only with the non-root parts (docs, scripts, review)
  and perform the root steps manually.

Do not try to disguise the request to get around an assistant's safety policy.

---

## Before you start

Read this once.

- **Root changes the TV.** You accept the risk. These steps use Vetro's root
  integration; there is no UEP bypass or unsigned boot script.
- You need a **Samsung account** for the signing certificate. Apps2Samsung uses
  the account to create a Public/Partner certificate for this TV.
- You need **Developer Mode** enabled and the TV on the same network as the
  computer used for the initial install.
- Start from **stock Samsung Home**. If another launcher has replaced Home,
  restore Samsung Home and uninstall that launcher first. Vetro expects Samsung
  Home to be the native Home app.
- After the cutover, Developer Mode's **Host PC IP becomes `127.0.0.1`** and
  normal SDB from your computer stops working. This is intentional. Management
  continues through the Vetro dashboard on port `8099`.
- The patches in `patches/` are applied to Vetro's installed files. A Vetro
  update will overwrite them; rerun the scripts after updating Vetro.

Have the physical remote handy to accept the WebSocket pairing prompt and
confirm dialogs. The M7 remote has no number pad; use the network helpers below.

---

## Find the TV's IP

The example IP that used to be in this guide belonged to one test network. Do
not use it. Find the address of **your** TV:

- On the TV: **Settings → General → Network → Network Status → IP Address**.
- Or look for the TV's MAC/hostname in your router's DHCP client list.

Give the TV a DHCP reservation if possible, so the address stays the same.

Set it once in the shell used for the commands below:

```bash
export TV_IP="192.168.1.50"   # example only - replace with your TV's IP
export HOST_IP="192.168.1.23" # example only - this computer's LAN IP
ping -c 1 "$TV_IP"
```

If a later shell cannot resolve `$TV_IP`, export it again.

---

## Enable Developer Mode without a number pad

The M7 smart remote has no numeric keypad, so `12345` and the Host PC IP have to
be entered over the network. There are two paths.

### A. Vetro is already installed

Vetro's dashboard can inject keys through its root agent. No pairing token is
needed.

```bash
# Open Apps on the TV first, then:
python3 scripts/vetro-key.py --tv "$TV_IP" digits 12345
```

The Developer Mode dialog opens. Select **Developer mode** and the **Host PC IP**
field first; the helper only types into the focused field. If Developer mode is
off, move to its toggle and press Return:

```bash
python3 scripts/vetro-key.py --tv "$TV_IP" key Return
```

Now set the **computer's** LAN IP (not the TV's IP) for the first install.
Keep this address until Vetro is installed; only then switch to `127.0.0.1`.

```bash
# macOS Wi-Fi; use your computer's LAN address on other systems
HOST_IP=$(ipconfig getifaddr en0)
python3 scripts/vetro-key.py --tv "$TV_IP" ip "$HOST_IP" --submit
```

For the later TV-local root cutover, type `127.0.0.1` instead:

```bash
python3 scripts/vetro-key.py --tv "$TV_IP" ip 127.0.0.1 --submit
```

`--submit` presses Down then Return. If the dialog layout differs, or the value
was not saved, send the focus/OK keys explicitly, for example:

```bash
python3 scripts/vetro-key.py --tv "$TV_IP" key Down Return
```

### B. Before Vetro is installed

Use Samsung's local WebSocket remote. It needs a one-time pairing approval on
the TV.

```bash
python3 -m pip install -r requirements.txt

# The TV shows "Allow"; accept it with the physical remote.
python3 scripts/tv-remote.py --tv "$TV_IP" --wait 60 --key KEY_HOME
```

Then open **Apps** on the TV (with the physical remote or the key commands),
and send the digits:

```bash
python3 scripts/tv-remote.py --tv "$TV_IP" --digits 12345
```

Set the computer IP, then confirm:

```bash
HOST_IP=$(ipconfig getifaddr en0)     # macOS example
python3 scripts/tv-remote.py --tv "$TV_IP" --ip "$HOST_IP"
python3 scripts/tv-remote.py --tv "$TV_IP" --key KEY_DOWN --key KEY_ENTER
```

The first command saves the pairing token in `.tv-token` (gitignored). If the
TV never shows an Allow prompt, enable **IP Remote** in the TV network settings
and try again.

### Verify Developer Mode

```bash
curl -s "http://$TV_IP:8001/api/v2/" | python3 -c \
  'import json,sys; d=json.load(sys.stdin)["device"]; print(d.get("developerMode"), d.get("developerIP"))'
```

`developerMode` must be `1` and `developerIP` must match the address you typed.
The REST API can lag until the dialog closes; power-cycling the TV makes it
authoritative.

---

## Step 1 — Install Apps2Samsung

Download the CLI for your computer from
[Apps2Samsung releases](https://github.com/Apps2Samsung/Apps2Samsung/releases).
For an Apple-silicon Mac:

```bash
curl -L -o apps2samsung.tar.gz \
  https://github.com/Apps2Samsung/Apps2Samsung/releases/download/v3.1.0/Apps2Samsung-cli-v3.1.0-osx-arm64.tar.gz
tar -xzf apps2samsung.tar.gz
./apps2samsung-cli --version
```

The desktop app works too. The CLI is used below because it can be scripted.

Check the TV:

```bash
./apps2samsung-cli tv "$TV_IP"
```

Developer Mode must be on and the TV must expose SDB. If it reports a
certificate is needed, the first install will open Samsung sign-in.

---

## Step 2 — Install Vetro with root integration

```bash
./apps2samsung-cli install "Vetro" --tv "$TV_IP" --allow-root --yes --launch
```

What happens:

- Apps2Samsung downloads Vetro `0.3.5`.
- Because Vetro requires restricted privileges, it signs with a **Partner**
  certificate. The first run opens Samsung sign-in.
- The app is installed as `vetrotvapp.app` and launched.
- Vetro serves its dashboard at `http://$TV_IP:8099`.

Verify:

```bash
curl http://$TV_IP:8099/status
```

The first launch may report the root agent as disconnected. That is expected
until the Host PC IP is changed in the next step.

### Set the TV-local SDB

On the TV:

1. Open **Apps**.
2. Send `12345` over the network:

   ```bash
   python3 scripts/vetro-key.py --tv "$TV_IP" digits 12345
   ```

3. Select the **Host PC IP** field.
4. Type `127.0.0.1` and confirm:

   ```bash
   python3 scripts/vetro-key.py --tv "$TV_IP" ip 127.0.0.1 --submit
   ```

5. **Power-cycle the TV** (unplug it or use Restart).

Wait up to 90 seconds. Then:

```bash
curl http://$TV_IP:8099/status
```

The response should include:

```json
"agent": {
  "connected": true,
  "uid": 0
}
```

From this point the TV roots itself at boot. Your computer no longer needs SDB.

---

## Step 3 — Apply the M7 patches

```bash
python3 scripts/apply-m7-patches.py --tv "$TV_IP"
```

This is idempotent. It writes backups as `*.m7bak` on the TV and:

- adds the native `XF86DiscretHDMI*` keys and `KEY_HDMI*` aliases;
- removes the dock's `--kill-on-home` guard;
- changes the Samsung Home pill to inject `XF86Home`;
- adds the 30s/90s dock boot watchdog;
- installs the rebuilt `tvlauncher-dotnet-m7.dll`;
- restarts Vetro and starts/refreshes the dock.

If it says the Vetro service is unavailable, open the **Vetro** app on the TV
once, wait 10 seconds, and run it again.

Verify the dock:

```bash
curl http://$TV_IP:8099/dock
```

`enabled` and `running` should both be `true`.

---

## Step 4 — Add the USB-C input tile

```bash
python3 scripts/setup-dock.py --tv "$TV_IP"
```

This writes:

```text
in-tv     TV      source:0
in-hdmi1  HDMI 1  source:13
in-hdmi2  HDMI 2  source:14
in-usbc   USB-C   source:41
```

If Vetro reports `The Home row is empty or unreadable`, add a few apps to
Samsung Home first. The dock's app row is built from Samsung Home's row.

---

## Step 5 — Install the remap rules

```bash
python3 scripts/setup-remap.py --tv "$TV_IP"
```

This posts the rules and starts the physical input filter:

| Button | evdev code | Action | Result |
|---|---:|---|---|
| Netflix | `226` | `KEY_HDMI1` | HDMI 1 |
| Disney+ | `626` | `KEY_HDMI2` | HDMI 2 |
| Prime Video | `221` | `KEY_USBC` | USB-C |

It selects `Smart Control 2016` (usually `/dev/input/event4`) automatically.
Use `--node /dev/input/eventN` if your remote appears elsewhere.

---

## Step 6 — Verify and reboot

```bash
python3 scripts/verify.py --tv "$TV_IP"
```

Expected:

```text
root agent: uid=0 ...
dock: running pid=...
rules: 226 -> HDMI1, 626 -> HDMI2, 221 -> USB-C
filter: /dev/input/event4 blocked=['226', '626', '221']
native Home: com.samsung.tv.csfs
OK: Vetro, dock, native Home, and the three remaps are healthy.
```

Now power-cycle once more and run `verify.py` again. The dock, root agent,
remapper rules and filter should all return without opening the Vetro app.

---

## Daily use

- **Home** opens the Vetro dock. Release the key; the dock stays.
- **Up** opens the inputs panel: TV, HDMI 1, HDMI 2, USB-C.
- **Samsung Home** pill opens Samsung's own Home.
- **Netflix / Disney+ / Prime Video** switch directly to HDMI 1 / HDMI 2 / USB-C.
- Other remote buttons pass through untouched.

The Vetro dashboard at `http://$TV_IP:8099` is the control panel for
launcher, remapper, app inventory, debloat, DNS and diagnostics.

---

## Optional debloat and tweaks

Use the Vetro dashboard, not blind shell commands.

- **Debloat / Components**: review each package before disabling it. Keep the
  launcher, input, network, certificate, and Samsung Home components.
- **App flags**: disable auto-start/auto-restart on apps you never use.
- **DNS / privacy**: Vetro can apply its DNS filter and HbbTV controls.
- **Quick wins**: review the suggested changes; do them one at a time.

Avoid disabling anything named `csfs`, `tv-viewer`, `appfw`, `sdbd`, `vconf`,
`systemd`, or the Vetro package. If the TV stops booting to Home, restore the
component you disabled through the same dashboard.

Debloating is optional. The input remap and launcher do not depend on it.

---

## Troubleshooting

### The dock is missing after boot

1. Check `curl http://$TV_IP:8099/status` — is the agent connected?
2. Check `/dock` — is it `enabled` but not `running`?
3. Refresh it:

   ```bash
   curl -X POST -H 'Content-Type: application/json' \
     -d '{"action":"refresh"}' http://$TV_IP:8099/dock
   ```

4. If the service is down, open the Vetro app on the TV once. The watchdog then
   starts the dock at 30s or 90s.

### App buttons still open Netflix/Disney/Prime

- Check `/input`: the filter must be `connected` and block `226`, `626`, `221`.
- Re-run `scripts/setup-remap.py`.
- If the filter is on the wrong device, find the right node with `GET /input`
  and pass `--node`.
- After a Vetro update, re-run `scripts/apply-m7-patches.py` — the aliases and
  native keys may have been overwritten.

### Samsung Home pill does nothing

The pill must use `key:XF86Home`, not `sys:com.samsung.tv.csfs`. Re-run
`scripts/apply-m7-patches.py`; it patches `dock-catalog.js` and refreshes the
dock.

### The Home dock closes as soon as I release Home

The patched `tvlauncher-dotnet-m7.dll` is missing or was replaced by a Vetro
update. Re-run `scripts/apply-m7-patches.py`.

### `The Home row is empty or unreadable`

Vetro builds the dock from Samsung Home's app row. Add a few apps to Samsung
Home, or make sure Samsung Home is the native Home app. Then refresh the dock.

### SDB stopped working from my computer

Expected: Host PC IP is `127.0.0.1`. Use the dashboard. To go back to computer
SDB, set Host PC IP to the computer's IP and reboot; the root agent will stop
working until it is set back.

### Vetro asks for Samsung sign-in again

The certificate is per-machine. Sign in and let Apps2Samsung create a new
certificate covering the TV's DUID.

---

## Rollback

Turn off the remapper filter:

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"mode":"off"}' http://$TV_IP:8099/input
```

Turn off the dock:

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"action":"disable"}' http://$TV_IP:8099/dock
```

Uninstall Vetro:

```bash
./apps2samsung-cli uninstall vetrotvapp.app --tv "$TV_IP"
```

If SDB is locked, set Host PC IP back to the computer's IP first and reboot.
Removing Vetro does not change Samsung Home, but it removes the root agent and
the remapper.

The M7 patch backups on the TV are `*.m7bak`; restore them only if you need the
stock Vetro files:

```text
/opt/usr/apps/vetrotvapp/res/wgt/service/control.js.m7bak
/opt/usr/apps/vetrotvapp/res/wgt/service/dock.js.m7bak
/opt/usr/apps/vetrotvapp/res/wgt/service/dock-catalog.js.m7bak
/opt/usr/apps/vetrotvapp/res/wgt/service/main.js.m7bak
/opt/usr/apps/vetrotvapp/res/wgt/native/dock/tvlauncher-dotnet.dll.m7bak
```

---

## Repository layout

```text
README.md                      this guide
patches/
  tvlauncher-dotnet-m7.dll     rebuilt dock with the Home-release fix
  Program.cs.patch             source diff for the dock fix
  inputs.tsv                   TV / HDMI 1 / HDMI 2 / USB-C
  remap-rules.json             physical-button rules
  README.md                    patch details and rebuild instructions
scripts/
  m7vetro.py                   Vetro dashboard/root-agent client
  tv-remote.py                 Samsung WebSocket pairing and key injection
  vetro-key.py                 key injection through the Vetro dashboard
  apply-m7-patches.py          idempotent M7 patch installer
  setup-dock.py                writes inputs, starts the dock
  setup-remap.py               installs rules and starts the filter
  verify.py                    read-only health check
requirements.txt               optional websocket-client dependency
docs/
  AI-AGENT.md                  machine-oriented runbook
  TROUBLESHOOTING.md           longer fault tree
```

---

## Credits and licence

- [Vetro](https://github.com/andrearicci93/vetro) — MIT, the launcher, dashboard
  and root integration. The patched dock binary is a modified Vetro build.
- [Apps2Samsung](https://github.com/Apps2Samsung/Apps2Samsung) — installer and
  certificate tooling.
- This repository's guide and scripts — MIT. See `LICENSE` and `NOTICE.md`.
