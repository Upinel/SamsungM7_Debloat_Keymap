#!/usr/bin/env python3
"""Read-only health check for the Vetro + M7 remap setup."""

from __future__ import annotations

import argparse
import sys

from m7vetro import M7Error, TV


EXPECTED = {"226": "KEY_HDMI1", "626": "KEY_HDMI2", "221": "KEY_USBC"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True)
    args = parser.parse_args()

    tv = TV(args.tv)
    failures: list[str] = []

    status = tv.wait_up(60)
    agent = status.get("agent", {})
    if not agent.get("connected"):
        failures.append("Vetro root agent is not connected")
    else:
        print(f"root agent: uid={agent.get('uid')} pid={agent.get('pid')}")

    state = tv.dock()
    if not state.get("enabled"):
        failures.append("Vetro dock is not enabled")
    if not state.get("running"):
        failures.append("Vetro dock is not running")
    else:
        print(f"dock: running pid={state.get('pid')}")

    labels = {entry.get("label") for entry in state.get("inputs", [])}
    for label in ("HDMI 1", "HDMI 2", "USB-C"):
        if label not in labels:
            failures.append(f"dock input missing: {label}")

    remap = tv.get("/remap", timeout=20)
    rules = {rule["trigger"]["value"]: rule["actions"][0].get("key") for rule in remap.get("rules", [])}
    for code, expected in EXPECTED.items():
        if rules.get(code) != expected:
            failures.append(f"remap {code}: expected {expected}, got {rules.get(code)}")
    if not failures:
        print("rules: 226 -> HDMI1, 626 -> HDMI2, 221 -> USB-C")

    inputs = tv.inputs().get("status", {})
    policy = inputs.get("policy", {})
    if not policy.get("connected"):
        failures.append("physical input filter is not connected")
    else:
        print(f"filter: {policy.get('node')} blocked={policy.get('blocked')}")

    home = tv.exec("vconftool get db/appfw/home_appid 2>&1").strip()
    if "com.samsung.tv.csfs" not in home:
        failures.append(f"native Home is not Samsung Home: {home}")
    else:
        print("native Home: com.samsung.tv.csfs")

    if failures:
        print("\nFAILED", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("\nOK: Vetro, dock, native Home, and the three remaps are healthy.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except M7Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
