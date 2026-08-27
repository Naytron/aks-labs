#!/usr/bin/env python3
import json
import concurrent.futures
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOSTS = {"github.com", "kubernetes.io", "learn.microsoft.com"}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


def discover_links() -> list[str]:
    links: set[str] = set()
    for markdown in ROOT.rglob("*.md"):
        if ".git" in markdown.parts:
            continue
        for link in LINK_PATTERN.findall(markdown.read_text(encoding="utf-8")):
            parsed = urllib.parse.urlparse(link)
            if parsed.hostname in ALLOWED_HOSTS:
                links.add(urllib.parse.urlunparse(parsed._replace(fragment="")))
    quiz_data = ROOT / "docs" / "_data" / "quiz"
    if quiz_data.is_dir():
        for data_file in quiz_data.glob("*.json"):
            data = json.loads(data_file.read_text(encoding="utf-8"))
            for question in data.get("questions", []):
                for resource in question.get("learnMore", []):
                    link = resource.get("url", "")
                    parsed = urllib.parse.urlparse(link)
                    if parsed.hostname in ALLOWED_HOSTS:
                        links.add(urllib.parse.urlunparse(parsed._replace(fragment="")))
    return sorted(links)


def check_link(url: str) -> tuple[str, int | str]:
    headers = {"User-Agent": "aks-labs-course-link-check/1.0"}
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, headers=headers, method="HEAD")
            with urllib.request.urlopen(request, timeout=20) as response:
                return url, response.status
        except urllib.error.HTTPError as error:
            if error.code in {401, 403, 405, 429}:
                if error.code == 405:
                    try:
                        request = urllib.request.Request(url, headers=headers, method="GET")
                        with urllib.request.urlopen(request, timeout=20) as response:
                            return url, response.status
                    except urllib.error.HTTPError as get_error:
                        return url, get_error.code
                return url, error.code
            if attempt == 1:
                return url, error.code
        except (TimeoutError, urllib.error.URLError) as error:
            if attempt == 1:
                return url, str(error)
        time.sleep(1)
    return url, "unknown failure"


def main() -> None:
    links = discover_links()
    failures: list[tuple[str, int | str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        for url, result in executor.map(check_link, links):
            if isinstance(result, int) and (result < 400 or result in {401, 403, 429}):
                continue
            failures.append((url, result))
    if failures:
        details = "\n".join(f"{result}: {url}" for url, result in failures)
        raise SystemExit(f"External link failures:\n{details}")
    print(f"Checked {len(links)} first-party external links.")


if __name__ == "__main__":
    main()
