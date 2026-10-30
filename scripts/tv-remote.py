#!/usr/bin/env python3
"""Pair with a Samsung TV and send remote keys over the local WebSocket.

This is the bootstrap path for Developer Mode before Vetro is installed. On
first use the TV asks to allow the connection; accept it with the physical
remote. The returned token is stored in .tv-token (gitignored).

Requires: pip install websocket-client
"""

from __future__ import annotations

import argparse
import base64
import json
import ssl
import sys
import time
from pathlib import Path

try:
    import websocket
except ImportError:
    print("install the dependency first: python3 -m pip install websocket-client", file=sys.stderr)
    raise SystemExit(2)


def find_token(value: object) -> str | None:
    if isinstance(value, dict):
        token = value.get("token")
        if isinstance(token, str) and token:
            return token
        for nested in value.values():
            found = find_token(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_token(nested)
            if found:
                return found
    return None


def connect(host: str, token: str | None, wait: int, token_file: Path):
    name = base64.b64encode(b"M7-Setup").decode("ascii")
    url = f"wss://{host}:8002/api/v2/channels/samsung.remote.control?name={name}"
    if token:
        url += f"&token={token}"
    ws = websocket.create_connection(
        url,
        timeout=max(wait, 8),
        sslopt={"cert_reqs": ssl.CERT_NONE},
    )

    first = None
    ws.settimeout(wait)
    try:
        first = ws.recv()
    except websocket.WebSocketTimeoutException:
        if not token:
            raise SystemExit(
                "No response from the TV. If it shows an Allow prompt, accept it with the "
                "physical remote, then rerun. Also check that IP Remote is enabled."
            ) from None
    else:
        try:
            payload = json.loads(first)
        except (TypeError, json.JSONDecodeError):
            payload = None
        found = find_token(payload)
        if found:
            token = found
            print(f"paired; token saved to {token_file}")
            token_file.write_text(token + "\n")
    return ws, token


def ip_keys(address: str) -> list[str]:
    octets = address.split(".")
    if len(octets) != 4:
        raise SystemExit(f"not an IPv4 address: {address}")
    keys: list[str] = []
    for index, octet in enumerate(octets):
        if not octet.isdigit() or not 0 <= int(octet) <= 255:
            raise SystemExit(f"not an IPv4 address: {address}")
        keys.extend(list(octet))
        if index != 3:
            keys.append("KEY_RIGHT")
    return keys


def send(ws, key: str, delay: float) -> None:
    ws.send(
        json.dumps(
            {
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Click",
                    "DataOfCmd": key,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey",
                },
            }
        )
    )
    print(f"  {key}")
    time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tv", required=True)
    parser.add_argument("--token-file", default=".tv-token")
    parser.add_argument("--wait", type=int, default=60, help="seconds to wait for the Allow prompt")
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--key", action="append", help="send a key name, repeatable")
    parser.add_argument("--digits", help="send a digit string")
    parser.add_argument("--ip", help="type an IPv4 address (Right between octets)")
    args = parser.parse_args()

    args.token_file = Path(args.token_file)
    token = args.token_file.read_text().strip() if args.token_file.is_file() else None
    ws, token = connect(args.tv, token, args.wait, args.token_file)

    try:
        if args.key:
            for key in args.key:
                send(ws, key, args.delay)
        elif args.digits:
            for char in args.digits:
                if not char.isdigit():
                    raise SystemExit(f"not a digit: {char}")
                send(ws, f"KEY_{char}", args.delay)
        elif args.ip:
            for key in ip_keys(args.ip):
                send(ws, key, args.delay)
        else:
            print("Connected. Use --key, --digits or --ip.")
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
