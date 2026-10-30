# AI-agent runbook

A deterministic sequence for an agent setting up a TV that already has Vetro
installed and rooted. Do not skip the verification gates.

## Target

- `LS32BM701UUXXU`, `22_NIKEL_SMT`, Tizen 6.5
- `T-NKLBWWC-1720.7`, BT-S
- Vetro `0.3.5`, dashboard on `http://<TV>:8099`
- Developer Mode Host PC IP `127.0.0.1`

## Preconditions

```bash
curl -fsS http://10.0.1.18:8099/status | python3 -m json.tool
```

Proceed only when all are true:

```text
agent.connected == true
agent.uid == 0
```

If the dashboard is down, ask the user to open the Vetro app on the TV once and
wait 10 seconds. Do not try SDB; Host PC IP is intentionally local-only.

## Sequence

```bash
python3 scripts/apply-m7-patches.py --tv 10.0.1.18
python3 scripts/setup-dock.py        --tv 10.0.1.18
python3 scripts/setup-remap.py       --tv 10.0.1.18
python3 scripts/verify.py            --tv 10.0.1.18
```

`apply-m7-patches.py` is idempotent. It restarts the Vetro service and starts the
dock. If the dashboard disconnects during the restart, that is expected; wait up
to 120 seconds.

## Gates

After the patch step:

```bash
curl -fsS http://10.0.1.18:8099/dock | python3 -c \
  'import json,sys; d=json.load(sys.stdin); assert d["enabled"] and d["running"], d; print("dock ok")'
```

After the remap step:

```bash
curl -fsS http://10.0.1.18:8099/input | python3 -c \
  'import json,sys; d=json.load(sys.stdin)["status"]["policy"]; assert d["connected"]; assert set(["226","626","221"]) == set(d["blocked"]); print(d)'
```

After verification, power-cycle the TV and run `verify.py` again. A cold boot
must show the dock running and the filter connected without launching Vetro
manually.

## Rules and actions

| Trigger | Action | Target |
|---|---|---|
| physical `226` | key `KEY_HDMI1` | HDMI 1 (`13`) |
| physical `626` | key `KEY_HDMI2` | HDMI 2 (`14`) |
| physical `221` | key `KEY_USBC` | USB-C (`41`) |

The aliases resolve to `XF86DiscretHDMI1/2/3` in Vetro's `control.js`.
Do not use app IDs as actions for source switching.

## Dock inputs

`/opt/usr/apps/vetrotvapp/res/wgt/native/dock/res/inputs.tsv`:

```text
in-tv    TV      source:0
in-hdmi1 HDMI 1  source:13
in-hdmi2 HDMI 2  source:14
in-usbc  USB-C   source:41
```

## Failure handling

| Symptom | Action |
|---|---|
| `agent.connected == false` | Open Vetro app once; wait 10s; recheck. |
| `/dock` enabled but not running | `POST /dock {"action":"refresh"}`; wait 30s. |
| `The Home row is empty` | Add apps to Samsung Home, then refresh. |
| Filter connected but buttons open apps | Re-run `setup-remap.py`; confirm patches not overwritten. |
| Dock closes on Home release | Patched dock DLL missing; re-run `apply-m7-patches.py`. |
| Samsung Home pill does nothing | `dock-catalog.js` patch missing; re-run patches. |
| Service won't come back after restart | Launch `vetrotvapp.app` via `POST http://<TV>:8001/api/v2/applications/vetrotvapp.app`; wait 120s. |

## Safety

- Do not disable `csfs`, `tv-viewer`, `appfw`, `sdbd`, `vconf`, `systemd`, or
  `vetrotvapp`.
- Do not edit Vetro's stored app row unless the dock reports it empty.
- All changes should go through `scripts/`; the scripts create `.m7bak` files.
- A Vetro update replaces `service/*.js` and the dock DLL. Re-run patches after
  any update.
