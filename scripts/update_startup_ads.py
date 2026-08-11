#!/usr/bin/env python3
from __future__ import annotations

import re
import os
import ssl
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "rewrite_remote" / "startup_ads" / "startup_ads.conf"

MOYU_URL = "https://ddgksf2013.top/rewrite/StartUpAds.conf"

SOURCES = [
    {
        "name": "blackmatrix7 AdvertisingLite",
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rewrite/QuantumultX/AdvertisingLite/AdvertisingLite.conf",
        "mode": "keyword",
    },
    {
        "name": "fmz200 wool_scripts rewrite",
        "url": "https://raw.githubusercontent.com/fmz200/wool_scripts/main/QuantumultX/rewrite/rewrite.snippet",
        "mode": "keyword",
    },
    {
        "name": "evilbutcher QuantumultX",
        "url": "https://raw.githubusercontent.com/evilbutcher/QuantumultX/main/QuantumultX.rewrite.conf",
        "mode": "evilbutcher",
    },
    {
        "name": "app2smile qidian",
        "url": "https://raw.githubusercontent.com/app2smile/rules/master/module/qidian.conf",
        "mode": "all_rules",
    },
    {
        "name": "app2smile tieba",
        "url": "https://raw.githubusercontent.com/app2smile/rules/master/module/tieba-qx.conf",
        "mode": "all_rules",
    },
    {
        "name": "app2smile zhihu",
        "url": "https://raw.githubusercontent.com/app2smile/rules/master/module/zhihu.conf",
        "mode": "all_rules",
    },
    {
        "name": "app2smile qqnews",
        "url": "https://raw.githubusercontent.com/app2smile/rules/master/module/qqnews.conf",
        "mode": "all_rules",
    },
]

RULE_RE = re.compile(
    r"\surl\s(?:reject|reject-200|reject-dict|reject-img|script-response-body|jsonjq-response-body|response-body)\b"
)

STARTUP_KEYWORD_RE = re.compile(
    r"splash|launch|startup|startpage|start_page|startPage|appstart|app_start|"
    r"appload|appLoad|boot|bootpage|welcome|openapp|openApp|openAppAd|"
    r"getStart|startUp|startup-logo|launcher|getsplash|getSplash|launch_ad|"
    r"real_time_launch|queryStartPage|GetAppStart|GetAppStartImg|routerAppSplash|"
    r"WapLaunchLogo|mwaSplash|OpenAPP|OPEN_SCREEN|screenSplash|bottomtab_tip|"
    r"platflashbox|platbanner|platstrongshell|floatbox|开屏|启动",
    re.I,
)


def fetch_text(url: str, *, user_agent: str = "Quantumult%20X") -> str:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    context = None
    if os.environ.get("ALLOW_INSECURE_TLS") == "1":
        context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        data = response.read()
    return data.decode("utf-8", errors="replace")


def assert_not_html(name: str, text: str) -> None:
    prefix = text.lstrip()[:120].lower()
    if prefix.startswith("<!doctype") or prefix.startswith("<html"):
        raise RuntimeError(f"{name} returned HTML instead of a rewrite file")


def update_time_from_moyu(text: str) -> str:
    match = re.search(r"@UpdateTime\s+([0-9-]+)", text)
    return match.group(1) if match else "unknown"


def split_moyu(text: str) -> tuple[list[str], list[str]]:
    body: list[str] = []
    host_lines: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*hostname\s*=", line):
            host_lines.append(line)
        else:
            body.append(line.rstrip())
    return body, host_lines


def should_keep_extra_rule(line: str, mode: str) -> bool:
    if mode == "keyword":
        return bool(STARTUP_KEYWORD_RE.search(line))
    if mode == "all_rules":
        return True
    if mode == "evilbutcher":
        return any(token in line for token in ("10086", "mobilebj", "gotokeep"))
    return False


def select_extra_rules(
    source_text: str, mode: str, seen_rules: set[str]
) -> list[str]:
    selected: list[str] = []
    for raw_line in source_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if line.startswith("hostname"):
            continue
        if not RULE_RE.search(line):
            continue
        if should_keep_extra_rule(line, mode) and line not in seen_rules:
            seen_rules.add(line)
            selected.append(line)
    return selected


def split_hosts(line: str) -> list[str]:
    if "=" not in line:
        return []
    return [part.strip() for part in line.split("=", 1)[1].split(",") if part.strip()]


def expand_groups(segment: str) -> list[str]:
    segment = segment.replace("?:", "")
    results = [segment]
    simple_group = re.compile(r"\(([^()]+)\)")

    for _ in range(8):
        changed = False
        next_results: list[str] = []
        for item in results:
            match = simple_group.search(item)
            if not match:
                next_results.append(item)
                continue

            alternatives = match.group(1).split("|")
            if len(alternatives) > 16:
                next_results.append(item[: match.start()] + "*" + item[match.end() :])
                changed = True
                continue

            for alternative in alternatives:
                next_results.append(
                    item[: match.start()] + alternative + item[match.end() :]
                )
            changed = True

        results = next_results[:300]
        if not changed:
            break

    return results


def clean_host(host: str) -> str | None:
    replacements = {
        r"\/": "/",
        r"\.": ".",
        r"\-": "-",
        r"\_": "_",
        r"\:": ":",
    }
    for old, new in replacements.items():
        host = host.replace(old, new)

    host = host.replace("^", "").replace("$", "")
    host = re.sub(r"\[a-zA-Z0-9_\-\]\+", "*", host)
    host = re.sub(r"\[a-zA-Z0-9_\-\]\*", "*", host)
    host = re.sub(r"\[[^\]]+\](?:\{[^}]+\}|\+|\*)?", "*", host)
    host = re.sub(r"\\w\+|\\w\*|\\d\+|\\d\*|\\d\{[^}]+\}", "*", host)
    host = re.sub(r"\.\*\??|\.\+\??", "*", host)
    host = host.replace("?", "").replace("+", "")
    host = host.replace("\\", "")
    host = host.strip(".-")
    host = host.split(":", 1)[0]
    host = re.sub(r"\*+", "*", host.lower())

    if not host or "/" in host or " " in host:
        return None
    if any(char in host for char in "()[]{}|"):
        return None
    if not re.search(r"[a-z0-9]", host):
        return None
    if not re.fullmatch(r"[a-z0-9.*_-]+", host):
        return None

    return host


def hosts_from_rule(line: str) -> list[str]:
    match = re.search(r"\\/\\/", line)
    if not match:
        return []

    rest = line[match.end() :]
    end = len(rest)
    for marker in (r"\/", "/", " "):
        index = rest.find(marker)
        if index != -1:
            end = min(end, index)

    segment = rest[:end]
    hosts: list[str] = []
    for candidate in expand_groups(segment):
        host = clean_host(candidate)
        if host:
            hosts.append(host)
    return hosts


def unique_hosts(host_lines: list[str], extra_rules: list[str]) -> list[str]:
    hosts: list[str] = []
    seen: set[str] = set()

    def add(host: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9.*_-]+", host):
            return
        key = host.lower()
        if key not in seen:
            seen.add(key)
            hosts.append(host)

    for line in host_lines:
        for host in split_hosts(line):
            add(host)

    for line in extra_rules:
        for host in hosts_from_rule(line):
            add(host)

    return hosts


def build() -> str:
    moyu_text = fetch_text(MOYU_URL)
    assert_not_html("MoYu StartUpAds", moyu_text)

    moyu_body, moyu_host_lines = split_moyu(moyu_text)
    upstream_date = update_time_from_moyu(moyu_text)
    seen_rules = {line.strip() for line in moyu_body if RULE_RE.search(line)}

    selected_by_source: list[tuple[str, str, list[str]]] = []
    for source in SOURCES:
        text = fetch_text(source["url"])
        assert_not_html(source["name"], text)
        selected = select_extra_rules(text, source["mode"], seen_rules)
        selected_by_source.append((source["name"], source["url"], selected))

    extra_rules = [line for _, _, lines in selected_by_source for line in lines]
    hosts = unique_hosts(moyu_host_lines, extra_rules)

    output: list[str] = [
        "#!name=聚合去开屏广告",
        "#!desc=Quantumult X rewrite：以墨鱼去开屏 V2.0 为主，补充公开 QX 去开屏规则。",
        "#!author=xihazhiwang",
        "#!homepage=https://github.com/xihazhiwang/quanx",
        f"#!date={upstream_date}",
        "",
        "# 主来源：",
        f"# - 墨鱼去开屏 V2.0: {MOYU_URL}",
        "# 补充来源：",
    ]

    for name, url, selected in selected_by_source:
        output.append(f"# - {name}: {url} ({len(selected)} extra rules)")

    output.extend(
        [
            "# 抓取提示：ddgksf2013.top/rewrite/StartUpAds.conf 需要使用 Quantumult X User-Agent 才返回 conf。",
            "# 说明：本文件为聚合规则，若某个 App 功能异常，优先注释对应 App 小节。",
            "",
            "# ======= 主规则：墨鱼去开屏 V2.0 ======= #",
            *moyu_body,
        ]
    )

    for name, _url, selected in selected_by_source:
        if not selected:
            continue
        output.append("")
        output.append(f"# ======= 补充规则：{name} ======= #")
        output.extend(selected)

    output.append("")
    output.append("hostname = " + ", ".join(hosts))
    output.append("")

    return "\n".join(output)


def main() -> int:
    try:
        content = build()
    except Exception as exc:  # noqa: BLE001 - keep workflow failure clear.
        print(f"update_startup_ads.py: {exc}", file=sys.stderr)
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
