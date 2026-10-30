# Troubleshooting

## 1. Determine what is alive

```bash
curl -sS http://10.0.1.18:8099/status
curl -sS http://10.0.1.18:8099/dock
curl -sS http://10.0.1.18:8099/input
curl -sS http://10.0.1.18:8099/remap
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
  -d '{"action":"refresh"}' http://10.0.1.18:8099/dock
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
python3 scripts/apply-m7-patches.py --tv 10.0.1.18
```

Confirm the installed DLL is the patched one:

```bash
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"cmd":"sha256sum /opt/usr/apps/vetrotvapp/res/wgt/native/dock/tvlauncher-dotnet.dll"}' \
  http://10.0.1.18:8099/exec
```

Expected SHA-256:

```text
bdb12475da8c77700f1c563f85cd7bca50f08cca51a81ddcfa6091780602ed7b
```

## 5. Samsung Home pill does nothing

The dock catalog row is still `sys:com.samsung.tv.csfs`.

```bash
python3 scripts/apply-m7-patches.py --tv 10.0.1.18
```

The patched row must be:

```text
samsunghome  Samsung Home  key:XF86Home  com.samsung.tv.csfs
```

Then refresh the dock.

## 6. App buttons open the streaming apps

Check:

```bash
curl -sS http://10.0.1.18:8099/input | python3 -m json.tool
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
python3 scripts/setup-remap.py --tv 10.0.1.18
```

If the remote is on another node, list selectable devices with `GET /input` and
run:

```bash
python3 scripts/setup-remap.py --tv 10.0.1.18 --node /dev/input/eventN
```

After a Vetro update, the `KEY_HDMI*` aliases may be gone. Re-run
`apply-m7-patches.py`, then `setup-remap.py`.

## 7. One button does not switch

Test the action manually:

```bash
curl -X POST -H 'Content-Type: application/json' \
  -d '{"type":"physical","value":"226"}' \
  http://10.0.1.18:8099/remap/run
```

A successful response is `{"ok":true,"sent":1,...}`. If it is, the key action
works and the physical filter is the problem. If it reports an unknown key,
the `control.js` patch is missing.

## 8. SDB no longer works from the computer

Expected after the cutover. Host PC IP is `127.0.0.1`. Use the dashboard. To
restore computer SDB:

1. Apps → `12345` → Host PC IP = computer IP.
2. Reboot.
3. The TV-local root agent will not start until it is set back to `127.0.0.1`.

## 9. Vetro update

Vetro updates replace `service/*.js` and the dock DLL. Re-apply:

```bash
python3 scripts/apply-m7-patches.py --tv 10.0.1.18
python3 scripts/setup-dock.py        --tv 10.0.1.18
python3 scripts/setup-remap.py       --tv 10.0.1.18
python3 scripts/verify.py            --tv 10.0.1.18
```

Saved `.m7bak` files are from the *original* Vetro version. Do not restore them
over a newer Vetro build; rerun the patches instead.

## 10. Full reset

```bash
# disable remap
curl -X POST -H 'Content-Type: application/json' -d '{"mode":"off"}' http://10.0.1.18:8099/input
# disable dock
curl -X POST -H 'Content-Type: application/json' -d '{"action":"disable"}' http://10.0.1.18:8099/dock
# uninstall
./apps2samsung-cli uninstall vetrotvapp.app --tv 10.0.1.18
```

Set Host PC IP back first if Apps2Samsung cannot reach SDB.
