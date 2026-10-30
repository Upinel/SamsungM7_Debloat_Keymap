#!/usr/bin/env python3
"""Write the M7 dock inputs and start/refresh the Vetro dock."""

from __future__ import annotations

import argparse
import sys

from m7vetro import M7Error, TV


INPUTS = """# the inputs panel (Up on the dock)
in-tv\tTV\tsource:0
in-hdmi1\tHDMI 1\tsource:13
in-hdmi2\tHDMI 2\tsource:14
in-usbc\tUSB-C\tsource:41
"""

DOCK_INPUTS = "/opt/usr/apps/vetrotvapp/res/wgt/native/dock/res/inputs.tsv"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True)
    parser.add_argument("--no-start", action="store_true", help="write inputs but leave the dock alone")
    args = parser.parse_args()

    tv = TV(args.tv)
    tv.wait_up(60)
    tv.backup_once(DOCK_INPUTS)
    tv.write_file(DOCK_INPUTS, INPUTS.encode("utf-8"))
    print("Dock inputs written: TV, HDMI 1, HDMI 2, USB-C")

    if args.no_start:
        return 0

    try:
        state = tv.start_dock()
    except M7Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(
            "If Vetro says the Home row is empty, add some apps to Samsung Home first "
            "(the dock builds its app row from Samsung Home).",
            file=sys.stderr,
        )
        return 1

    print(f"Dock running={state.get('running')} pid={state.get('pid')}")
    for entry in state.get("inputs", []):
        print(f"  {entry.get('label')}: {entry.get('appId')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except M7Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
