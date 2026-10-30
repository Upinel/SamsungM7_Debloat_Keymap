#!/usr/bin/env python3
"""Apply the M7-specific Vetro fixes through the Vetro root agent.

Safe to re-run: every edit is guarded by a marker and every original file is
copied to <name>.m7bak once.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from m7vetro import M7Error, TV


CONTROL_KEYS_OLD = "'XF86ChannelList', 'XF86ChannelGuide', 'XF86DiscretSourceTV',"
CONTROL_KEYS_NEW = (
    "'XF86ChannelList', 'XF86ChannelGuide', 'XF86DiscretSourceTV', "
    "'XF86DiscretHDMI1', 'XF86DiscretHDMI2', 'XF86DiscretHDMI3',"
)
CONTROL_ALIASES = """
LAN_KEYS.KEY_HDMI1 = 'XF86DiscretHDMI1';
LAN_KEYS.KEY_HDMI2 = 'XF86DiscretHDMI2';
LAN_KEYS.KEY_USBC = 'XF86DiscretHDMI3';
"""
DOCK_GUARD = "' --hidden --home-code ' + HOME_CODE + ' --kill-on-home ' + HOME_APP;"
DOCK_NO_GUARD = "' --hidden --home-code ' + HOME_CODE;"
CATALOG_OLD = "'samsunghome\\tSamsung Home\\tsys:com.samsung.tv.csfs'"
CATALOG_NEW = "'samsunghome\\tSamsung Home\\tkey:XF86Home\\tcom.samsung.tv.csfs'"
WATCHDOG_MARK = "M7 boot recovery"
WATCHDOG = """
// M7 boot recovery: the root agent can connect before Wayland/EFL is ready, and a
// dock started at that moment can exit without a useful error. Retry after the
// desktop has settled, and once more for slow boots.
[30000, 90000].forEach(function (ms) {
  setTimeout(function () {
    try {
      if (dock.readState().enabled) {
        dock.nextTry = 0;
        dock.supervise(!!platform.status().agent.connected).catch(function () {});
      }
    } catch (e) { /* keep the service alive */ }
  }, ms);
});
"""

SERVICE = "/opt/usr/apps/vetrotvapp/res/wgt/service"
DOCK = "/opt/usr/apps/vetrotvapp/res/wgt/native/dock"


def patch_service_file(tv: TV, name: str, replacements: list[tuple[str, str]], marker: str) -> bool:
    path = f"{SERVICE}/{name}"
    text = tv.read_file(path)
    if marker in text:
        print(f"  {name}: already patched")
        return False
    updated = text
    for old, new in replacements:
        if old not in updated:
            raise M7Error(f"{name}: expected text not found; Vetro version may differ")
        updated = updated.replace(old, new, 1)
    tv.backup_once(path)
    tv.write_file(path, updated.encode("utf-8"))
    print(f"  {name}: patched")
    return True


def patch_dock_guard(tv: TV) -> bool:
    path = f"{SERVICE}/dock.js"
    text = tv.read_file(path)
    if DOCK_GUARD not in text:
        print("  dock.js: Home guard already removed")
        return False
    tv.backup_once(path)
    tv.write_file(path, text.replace(DOCK_GUARD, DOCK_NO_GUARD, 1).encode("utf-8"))
    print("  dock.js: Home guard removed")
    return True


def patch_watchdog(tv: TV) -> bool:
    path = f"{SERVICE}/main.js"
    text = tv.read_file(path)
    if WATCHDOG_MARK in text:
        print("  main.js: watchdog already present")
        return False
    tv.backup_once(path)
    tv.write_file(path, (text.rstrip() + "\n" + WATCHDOG).encode("utf-8"))
    print("  main.js: watchdog added")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True, help="TV IP, for example 10.0.1.18")
    parser.add_argument(
        "--dock-dll",
        default=str(Path(__file__).resolve().parent.parent / "patches" / "tvlauncher-dotnet-m7.dll"),
        help="patched tvlauncher-dotnet.dll",
    )
    parser.add_argument("--skip-dll", action="store_true", help="leave the installed dock binary alone")
    parser.add_argument("--skip-restart", action="store_true", help="do not restart Vetro afterwards")
    args = parser.parse_args()

    tv = TV(args.tv)
    status = tv.wait_up(60)
    print(f"Vetro {status.get('app', {}).get('version', '?')} on {args.tv}")

    changed = False
    changed |= patch_service_file(
        tv,
        "control.js",
        [(CONTROL_KEYS_OLD, CONTROL_KEYS_NEW)],
        "XF86DiscretHDMI1",
    )
    # The aliases are appended so they are safe even on a Vetro build whose KEYS
    # line already has the three native names.
    control_path = f"{SERVICE}/control.js"
    control = tv.read_file(control_path)
    if "LAN_KEYS.KEY_HDMI1" not in control:
        tv.backup_once(control_path)
        tv.write_file(control_path, (control.rstrip() + "\n" + CONTROL_ALIASES).encode("utf-8"))
        print("  control.js: KEY_HDMI aliases added")
        changed = True

    changed |= patch_dock_guard(tv)
    changed |= patch_service_file(tv, "dock-catalog.js", [(CATALOG_OLD, CATALOG_NEW)], "key:XF86Home")
    changed |= patch_watchdog(tv)

    if not args.skip_dll:
        dll = Path(args.dock_dll)
        if not dll.is_file():
            raise M7Error(f"missing {dll}")
        tv.backup_once(f"{DOCK}/tvlauncher-dotnet.dll")
        tv.write_file(f"{DOCK}/tvlauncher-dotnet.dll", dll.read_bytes())
        print(f"  dock binary: {dll.name} installed")
        changed = True

    if args.skip_restart:
        print("Patches written. Restart Vetro and refresh the dock when ready.")
        return 0

    print("Restarting Vetro service...")
    tv.restart_service()
    print("Starting/refreshing the dock...")
    state = tv.start_dock()
    print(f"  dock running={state.get('running')} pid={state.get('pid')}")
    print("M7 patches applied.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except M7Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
