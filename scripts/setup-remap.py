#!/usr/bin/env python3
"""Install the Netflix / Disney+ / Prime Video source rules and start the filter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from m7vetro import M7Error, TV


DEFAULT_RULES = Path(__file__).resolve().parent.parent / "patches" / "remap-rules.json"


def pick_device(devices: list[dict], wanted: str | None) -> dict:
    if wanted:
        for device in devices:
            if device.get("node") == wanted:
                return device
        raise M7Error(f"input node not found: {wanted}")
    for device in devices:
        if device.get("selectable") and "smart control 2016" in device.get("name", "").lower():
            return device
    for device in devices:
        if device.get("selectable"):
            return device
    raise M7Error("no selectable remote input device found")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True)
    parser.add_argument("--rules", default=str(DEFAULT_RULES))
    parser.add_argument("--node", help="override the input node, e.g. /dev/input/event4")
    parser.add_argument("--disable", action="store_true", help="turn the filter off")
    args = parser.parse_args()

    tv = TV(args.tv)
    tv.wait_up(60)

    if args.disable:
        tv.stop_filter()
        print("Input filter disabled.")
        return 0

    document = json.loads(Path(args.rules).read_text())
    rules = document["rules"] if isinstance(document, dict) else document
    result = tv.remap_rules(rules)
    print(f"Rules installed: {len(result.get('rules', []))}")

    inventory = tv.inputs()
    device = pick_device(inventory.get("devices", []), args.node)
    status = tv.start_filter(device["node"])
    policy = status.get("status", {}).get("policy", {})
    print(f"Filter: {policy.get('node')} ({policy.get('device')})")
    print(f"Blocked: {', '.join(policy.get('blocked', []))}")

    for rule in rules:
        action = rule["actions"][0]
        print(f"  {rule['trigger']['value']}: {rule['id']} -> {action['key']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (M7Error, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
