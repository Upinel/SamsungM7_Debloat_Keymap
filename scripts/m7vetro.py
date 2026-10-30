#!/usr/bin/env python3
"""Small client for a Vetro-managed Samsung M7.

Only the Python standard library is used. Every change goes through Vetro's
root agent on the TV, so this works while Developer Mode's Host PC IP is
127.0.0.1 and normal SDB from this machine is locked out.
"""

from __future__ import annotations

import base64
import json
import shlex
import time
import urllib.error
import urllib.request
from typing import Any


VETRO_PORT = 8099
REST_PORT = 8001
APP_ID = "vetrotvapp.app"
UPLOAD_PATH = "/tmp/m7vetro.upload"
CHUNK = 8 * 1024


class M7Error(RuntimeError):
    pass


def _request(
    url: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
    method: str | None = None,
) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = method or "POST"
    else:
        method = method or "GET"
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode("utf-8", "replace")


class TV:
    def __init__(self, host: str, vetro_port: int = VETRO_PORT, rest_port: int = REST_PORT):
        self.host = host
        self.base = f"http://{host}:{vetro_port}"
        self.rest = f"http://{host}:{rest_port}"

    # ---------------------------------------------------------------- basics

    def get(self, path: str, timeout: int = 30) -> Any:
        return _request(self.base + path, timeout=timeout)

    def post(self, path: str, payload: dict[str, Any], timeout: int = 60) -> Any:
        return _request(self.base + path, payload, timeout=timeout)

    def exec(self, command: str, timeout: int = 60) -> str:
        """Run a command as root through Vetro's /exec endpoint."""
        result = self.post("/exec", {"cmd": command}, timeout=timeout)
        if not isinstance(result, dict):
            raise M7Error(f"Unexpected /exec response: {result!r}")
        if result.get("error"):
            raise M7Error(str(result["error"]))
        if result.get("timed_out"):
            raise M7Error("TV command timed out")
        if result.get("exit_code", 0) != 0:
            raise M7Error(
                (result.get("stderr") or result.get("output") or "TV command failed").strip()
            )
        return result.get("output", "")

    def wait_up(self, seconds: int = 120) -> dict[str, Any]:
        deadline = time.time() + seconds
        last: Exception | None = None
        while time.time() < deadline:
            try:
                status = self.get("/status", timeout=5)
                if isinstance(status, dict):
                    return status
            except Exception as exc:  # noqa: BLE001 - this is polling
                last = exc
            time.sleep(3)
        raise M7Error(f"Vetro dashboard did not come up: {last}")

    # ------------------------------------------------------------ files over /exec

    def read_file(self, path: str, timeout: int = 60) -> str:
        return self.exec(f"cat {shlex.quote(path)}", timeout=timeout)

    def write_file(self, path: str, data: bytes, mode: str = "644") -> None:
        self.exec(f"rm -f {UPLOAD_PATH}")
        encoded = base64.b64encode(data).decode("ascii")
        for start in range(0, len(encoded), CHUNK):
            piece = encoded[start : start + CHUNK]
            # 8 KiB of base64 keeps the JSON body well below Vetro's request limit.
            self.exec(f"printf %s {shlex.quote(piece)} | base64 -d >> {UPLOAD_PATH}")
        self.exec(
            f"cp {UPLOAD_PATH} {shlex.quote(path)} && chmod {mode} {shlex.quote(path)} && rm -f {UPLOAD_PATH}"
        )

    def backup_once(self, path: str) -> None:
        backup = path + ".m7bak"
        self.exec(
            f"if [ -e {shlex.quote(path)} ] && [ ! -e {shlex.quote(backup)} ]; "
            f"then cp -p {shlex.quote(path)} {shlex.quote(backup)}; fi"
        )

    # ---------------------------------------------------------------- service

    def restart_service(self) -> dict[str, Any]:
        try:
            status = self.get("/status", timeout=8)
            pid = status.get("self", {}).get("pid") if isinstance(status, dict) else None
        except Exception:
            pid = None
        if pid:
            try:
                # /exec dies with the service, so a dropped response is expected.
                self.exec(f"kill -9 {pid}", timeout=8)
            except Exception:
                pass
        try:
            _request(
                f"{self.rest}/api/v2/applications/{APP_ID}",
                payload=None,
                timeout=10,
                method="POST",
            )
        except Exception:
            pass
        return self.wait_up(120)

    # ---------------------------------------------------------------- dock

    def dock(self) -> dict[str, Any]:
        result = self.get("/dock", timeout=30)
        if not isinstance(result, dict):
            raise M7Error(f"Unexpected /dock response: {result!r}")
        return result

    def start_dock(self) -> dict[str, Any]:
        state = self.dock()
        action = "refresh" if state.get("enabled") else "enable"
        try:
            self.post("/dock", {"action": action}, timeout=90)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise M7Error(f"Vetro could not start the dock: {body}") from exc
        deadline = time.time() + 90
        while time.time() < deadline:
            state = self.dock()
            if state.get("running"):
                return state
            time.sleep(2)
        raise M7Error("The dock did not reach a running state")

    def inputs(self) -> dict[str, Any]:
        result = self.get("/input", timeout=30)
        if not isinstance(result, dict):
            raise M7Error(f"Unexpected /input response: {result!r}")
        return result

    def remap_rules(self, rules: list[dict[str, Any]]) -> dict[str, Any]:
        result = self.post("/remap", {"rules": rules}, timeout=30)
        if not isinstance(result, dict) or not result.get("ok"):
            raise M7Error(f"Remap rules rejected: {result!r}")
        return result

    def start_filter(self, node: str) -> dict[str, Any]:
        result = self.post("/input", {"device": node, "mode": "filter"}, timeout=60)
        if not isinstance(result, dict) or not result.get("ok"):
            raise M7Error(f"Input filter rejected: {result!r}")
        return result

    def stop_filter(self) -> dict[str, Any]:
        return self.post("/input", {"mode": "off"}, timeout=30)
