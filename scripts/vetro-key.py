#!/usr/bin/env python3
"""Send remote keys through Vetro's /control endpoint.

Useful when the M7 smart remote has no number pad and Developer Mode needs
12345 or an IP address. Vetro must already be installed and its root agent
connected; no Samsung WebSocket token is needed.
"""

from __future__ import annotations

import argparse
import sys
import time

from m7vetro import M7Error, TV


def send(tv: TV, key: str, delay: float) -> None:
    result = tv.post("/control", {"key": key}, timeout=15)
    if not isinstance(result, dict) or not result.get("ok"):
        raise M7Error(f"key {key!r} rejected: {result!r}")
    print(f"  {key}")
    time.sleep(delay)


def ip_keys(address: str) -> list[str]:
    octets = address.split(".")
    if len(octets) != 4:
        raise M7Error(f"not an IPv4 address: {address}")
    keys: list[str] = []
    for index, octet in enumerate(octets):
        if not octet.isdigit() or not 0 <= int(octet) <= 255:
            raise M7Error(f"not an IPv4 address: {address}")
        keys.extend(list(octet))
        if index != 3:
            keys.append("Right")
    return keys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True)
    parser.add_argument("--delay", type=float, default=0.35)
    sub = parser.add_subparsers(dest="command", required=True)

    key = sub.add_parser("key", help="send one or more Vetro key names")
    key.add_argument("keys", nargs="+", help="e.g. Down Return 1 2 3")

    digits = sub.add_parser("digits", help="send a digit string")
    digits.add_argument("digits")

    ip = sub.add_parser("ip", help="type an IPv4 address into the focused field")
    ip.add_argument("address")
    ip.add_argument("--submit", action="store_true", help="press Down then Return afterwards")

    sub.add_parser("ok", help="press Down then Return")

    args = parser.parse_args()
    tv = TV(args.tv)
    tv.wait_up(30)

    if args.command == "key":
        for name in args.keys:
            send(tv, name, args.delay)
    elif args.command == "digits":
        for char in args.digits:
            if not char.isdigit():
                raise M7Error(f"not a digit: {char}")
            send(tv, char, args.delay)
    elif args.command == "ip":
        for name in ip_keys(args.address):
            send(tv, name, args.delay)
        if args.submit:
            send(tv, "Down", args.delay)
            send(tv, "Return", args.delay)
    elif args.command == "ok":
        send(tv, "Down", args.delay)
        send(tv, "Return", args.delay)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except M7Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
