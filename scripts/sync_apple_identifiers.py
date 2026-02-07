#!/usr/bin/env python3
"""同步 Apple 设备 identifiers 映射数据到 devicemodel/data。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import time
import subprocess
import sys
import urllib.parse
from typing import Dict, Tuple

UPSTREAM_OWNER = "kyle-seongwoo-jun"
UPSTREAM_REPO = "apple-device-identifiers"
UPSTREAM_FULL = f"{UPSTREAM_OWNER}/{UPSTREAM_REPO}"

FILES = {
    "ios": "ios-device-identifiers.json",
    "macos": "mac-device-identifiers.json",
    "tvos": "tvos-device-identifiers.json",
    "watchos": "watchos-device-identifiers.json",
    "visionos": "visionos-device-identifiers.json",
}

MIN_COUNTS = {
    "ios": 100,
    "macos": 50,
    "tvos": 5,
    "watchos": 20,
    "visionos": 1,
}

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "devicemodel" / "data"
UPSTREAM_META_PATH = DATA_DIR / "UPSTREAM.json"
LICENSE_PATH = DATA_DIR / "LICENSE.apple-device-identifiers.txt"
SYNC_REPORT_PATH = ROOT / "sync-report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync apple-device-identifiers data")
    parser.add_argument("--ref", default="", help="指定 upstream ref（tag/branch/sha）")
    parser.add_argument("--tag", default="", help="指定 upstream release tag")
    parser.add_argument("--sha", default="", help="指定 upstream commit sha")
    return parser.parse_args()


def github_api(path: str, token: str) -> dict:
    url = f"https://api.github.com{path}"
    headers = [
        "Accept: application/vnd.github+json",
        "User-Agent: device-parser-sync-script",
    ]
    if token:
        headers.append("Authorization: Bearer " + token)

    raw = request_with_retry(url, headers)
    return json.loads(raw.decode("utf-8"))


def resolve_upstream_ref(args: argparse.Namespace, token: str) -> Tuple[str, str, str]:
    if args.sha:
        sha = args.sha.strip()
        if not sha:
            raise ValueError("--sha 不能为空")
        return sha, "sha", sha

    if args.tag:
        tag = args.tag.strip()
        if not tag:
            raise ValueError("--tag 不能为空")
        sha = resolve_commit_for_ref(tag, token)
        return tag, "tag", sha

    if args.ref:
        ref = args.ref.strip()
        if not ref:
            raise ValueError("--ref 不能为空")
        sha = resolve_commit_for_ref(ref, token)
        return ref, "ref", sha

    # 1) 优先 latest release
    try:
        latest = github_api(f"/repos/{UPSTREAM_FULL}/releases/latest", token)
        tag = str(latest.get("tag_name", "")).strip()
        if tag:
            sha = resolve_commit_for_ref(tag, token)
            return tag, "tag", sha
    except RuntimeError as exc:
        if not should_ignore_api_error(exc):
            raise

    # 2) fallback: tags 列表第一个
    try:
        tags = github_api(f"/repos/{UPSTREAM_FULL}/tags?per_page=1", token)
        if isinstance(tags, list) and tags:
            tag = str(tags[0].get("name", "")).strip()
            if tag:
                sha = resolve_commit_for_ref(tag, token)
                return tag, "tag", sha
    except RuntimeError as exc:
        if not should_ignore_api_error(exc):
            raise

    # 3) fallback: main
    sha = resolve_commit_for_ref("main", token)
    return "main", "ref", sha


def resolve_commit_for_ref(ref: str, token: str) -> str:
    safe_ref = urllib.parse.quote(ref, safe="")
    data = github_api(f"/repos/{UPSTREAM_FULL}/commits/{safe_ref}", token)
    sha = str(data.get("sha", "")).strip()
    if not sha:
        raise RuntimeError(f"无法解析 ref={ref} 的 commit sha")
    return sha


def download_raw(ref: str, path: str) -> bytes:
    safe_ref = urllib.parse.quote(ref, safe="")
    url = f"https://raw.githubusercontent.com/{UPSTREAM_FULL}/{safe_ref}/{path}"
    return request_with_retry(url, ["User-Agent: device-parser-sync-script"])


def request_with_retry(url: str, headers: list[str], retries: int = 4) -> bytes:
    delay = 1.0
    last_err: Exception | None = None

    curl_args = [
        "curl",
        "--silent",
        "--show-error",
        "--fail",
        "--location",
        "--connect-timeout",
        "15",
        "--max-time",
        "45",
    ]

    header_args: list[str] = []
    for header in headers:
        header_args.extend(["-H", header])

    for attempt in range(retries):
        try:
            completed = subprocess.run(
                [*curl_args, *header_args, url],
                check=True,
                capture_output=True,
            )
            return completed.stdout
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if attempt == retries - 1:
                break
            time.sleep(delay)
            delay = min(delay * 2, 8)

    raise RuntimeError(f"请求失败: {url}: {last_err}") from last_err


def should_ignore_api_error(exc: RuntimeError) -> bool:
    text = str(exc)
    return "404" in text or "403" in text


def validate_mapping(blob: bytes, kind: str) -> Dict[str, str]:
    try:
        data = json.loads(blob.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{kind} 数据不是合法 JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"{kind} 数据格式错误：期望 object")
    min_count = MIN_COUNTS.get(kind, 20)
    if len(data) < min_count:
        raise RuntimeError(f"{kind} 数据条数过少：{len(data)} < {min_count}")

    normalized: Dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            raise RuntimeError(f"{kind} 数据存在非字符串键: {key!r}")

        resolved = normalize_value(value)
        if resolved == "":
            raise RuntimeError(f"{kind} 数据值无法解析: {key!r} -> {value!r}")
        normalized[key] = resolved

    if kind == "ios" and not any(k.startswith("iPhone") for k in normalized):
        raise RuntimeError("ios 数据校验失败：缺少 iPhone 前缀 key")

    return normalized


def normalize_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return ""


def write_json(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(ref: str, ref_kind: str, sha: str, counts: dict) -> None:
    utc_now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Sync Report",
        "",
        f"- Upstream: `{UPSTREAM_FULL}`",
        f"- Ref: `{ref_kind}:{ref}`",
        f"- SHA: `{sha}`",
        f"- SyncedAt: `{utc_now}`",
        "",
        "## Counts",
        "",
        f"- ios: `{counts['ios']}`",
        f"- macos: `{counts['macos']}`",
        f"- tvos: `{counts['tvos']}`",
        f"- watchos: `{counts['watchos']}`",
        f"- visionos: `{counts['visionos']}`",
        "",
    ]
    SYNC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    token = os.getenv("GITHUB_TOKEN", "").strip()

    ref, ref_kind, sha = resolve_upstream_ref(args, token)

    counts = {}
    for kind, file_name in FILES.items():
        blob = download_raw(ref, file_name)
        mapping = validate_mapping(blob, kind)
        out_path = DATA_DIR / file_name
        write_json(out_path, mapping)
        counts[kind] = len(mapping)

    license_blob = download_raw(ref, "LICENSE")
    LICENSE_PATH.write_bytes(license_blob)

    utc_now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        "upstream_repo": UPSTREAM_FULL,
        "upstream_ref": f"{ref_kind}:{ref}",
        "upstream_sha": sha,
        "synced_at_utc": utc_now,
        "counts": counts,
    }
    write_json(UPSTREAM_META_PATH, meta)
    write_report(ref, ref_kind, sha, counts)

    print("同步完成:")
    print(f"- upstream={UPSTREAM_FULL}")
    print(f"- ref={ref_kind}:{ref}")
    print(f"- sha={sha}")
    print(f"- counts={counts}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"同步失败: {exc}", file=sys.stderr)
        raise SystemExit(1)
