# Troubleshooting

## Set your TV IP

```bash
export TV_IP="192.168.1.50"   # example only - replace with your TV's IP
export HOST_IP="192.168.1.23" # example only - this computer's LAN IP
```

All commands below use `$TV_IP` and `$HOST_IP`. Earlier revisions used a test-LAN address;
that address is not part of this guide.


## Developer Mode: 12345 and Host PC IP

The M7 remote has no digit keys.

If Vetro is running:

```bash
python3 scripts/vetro-key.py --tv "$TV_IP" digits 12345
python3 scripts/vetro-key.py --tv "$TV_IP" ip "$HOST_IP" --submit
```

Before Vetro is installed, pair the Samsung WebSocket remote once:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/tv-remote.py --tv "$TV_IP" --wait 60 --key KEY_HOME
# accept the Allow prompt on the TV with the physical remote
python3 scripts/tv-remote.py --tv "$TV_IP" --digits 12345
python3 scripts/tv-remote.py --tv "$TV_IP" --ip "$HOST_IP"
python3 scripts/tv-remote.py --tv "$TV_IP" --key KEY_DOWN --key KEY_ENTER
```

`HOST_IP` is the computer's LAN address. For the TV-local root cutover use
`127.0.0.1`. Verify with the REST API's `developerMode` and `developerIP`.

If the dialog layout is different, send focus keys one at a time and confirm
which field is selected before typing.

## 1. Determine what is alive

```bash
curl -sS http://$TV_IP:8099/status
curl -sS http://$TV_IP:8099/dock
curl -sS http://$TV_IP:8099/input
curl -sS http://$TV_IP:8099/remap
```

The three layers are independent:

| Layer | Healthy sign |
|---|---|
| Vetro service | `/status` responds |
| Root agent | `agent.connected` and `agent.uid == 0` |
| Dock | `/dock` `enabled` and `running` |
| Remapper | `/input` policy `connected`, codes blocked |
| Rules | `/remap` has 3 rules |

## 2. Dashboard is down

The Vetro app service did not start or crashed.

1. On the TV, open the **Vetro** app from Samsung Home or the Apps screen.
2. Wait 10–20 seconds.
3. Recheck `/status`.

If it still does not start, reboot the TV and wait up to 90 seconds. Vetro's
service is `on-boot`; the root agent can take a minute on a cold boot.

## 3. Agent is connected but dock is not running

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"action":"refresh"}' http://$TV_IP:8099/dock
```

Wait 30 seconds. The patched service also retries at 30s and 90s after boot.

If it reports `The Home row is empty or unreadable`:

- Make sure `com.samsung.tv.csfs` is the native Home app.
- Add a few apps to Samsung Home, then refresh.
- The dock builds its app row from Samsung Home's row.

Check `/dock` for `log`, `error`, `failures`.

## 4. Dock closes immediately on Home release

The patched dock binary was replaced or never installed.

```bash
python3 scripts/apply-m7-patches.py --tv "$TV_IP"
```

Confirm the installed DLL is the patched one:

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"cmd":"sha256sum /opt/usr/apps/vetrotvapp/res/wgt/native/dock/tvlauncher-dotnet.dll"}' \
  http://$TV_IP:8099/exec
```

Expected SHA-256:

```text
bdb12475da8c77700f1c563f85cd7bca50f08cca51a81ddcfa6091780602ed7b
```

## 5. Samsung Home pill does nothing

The dock catalog row is still `sys:com.samsung.tv.csfs`.

```bash
python3 scripts/apply-m7-patches.py --tv "$TV_IP"
```

The patched row must be:

```text
samsunghome  Samsung Home  key:XF86Home  com.samsung.tv.csfs
```

Then refresh the dock.

## 6. App buttons open the streaming apps

Check:

```bash
curl -sS http://$TV_IP:8099/input | python3 -m json.tool
```

Healthy:

```json
"policy": {
  "mode": "filter",
  "node": "/dev/input/event4",
  "connected": true,
  "blocked": ["226", "626", "221"]
}
```

If not, rerun:

```bash
python3 scripts/setup-remap.py --tv "$TV_IP"
```

If the remote is on another node, list selectable devices with `GET /input` and
run:

```bash
python3 scripts/setup-remap.py --tv "$TV_IP" --node /dev/input/eventN
```

After a Vetro update, the `KEY_HDMI*` aliases may be gone. Re-run
`apply-m7-patches.py`, then `setup-remap.py`.

## 7. One button does not switch

Test the action manually:

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"type":"physical","value":"226"}' \
  http://$TV_IP:8099/remap/run
```

A successful response is `{"ok":true,"sent":1,...}`. If it is, the key action
works and the physical filter is the problem. If it reports an unknown key,
the `control.js` patch is missing.

## 8. SDB no longer works from the computer

Expected after the cutover. Host PC IP is `127.0.0.1`. Use the dashboard. To
restore computer SDB:

1. Open Apps and send `12345` with `scripts/vetro-key.py` (or `scripts/tv-remote.py`
   before Vetro is installed), then set Host PC IP = computer IP.
2. Reboot.
3. The TV-local root agent will not start until it is set back to `127.0.0.1`.

## 9. Vetro update

Vetro updates replace `service/*.js` and the dock DLL. Re-apply:

```bash
python3 scripts/apply-m7-patches.py --tv "$TV_IP"
python3 scripts/setup-dock.py        --tv "$TV_IP"
python3 scripts/setup-remap.py       --tv "$TV_IP"
python3 scripts/verify.py            --tv "$TV_IP"
```

Saved `.m7bak` files are from the *original* Vetro version. Do not restore them
over a newer Vetro build; rerun the patches instead.

## 10. Full reset

```bash
# disable remap
curl -X POST -H 'Content-Type: application/json' -d '{"mode":"off"}' http://$TV_IP:8099/input
# disable dock
curl -X POST -H 'Content-Type: application/json' -d '{"action":"disable"}' http://$TV_IP:8099/dock
# uninstall
./apps2samsung-cli uninstall vetrotvapp.app --tv "$TV_IP"
```

Set Host PC IP back first if Apps2Samsung cannot reach SDB.
