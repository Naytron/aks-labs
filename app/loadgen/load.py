#!/usr/bin/env python3
import argparse
import concurrent.futures
import json
import random
import time
import urllib.error
import urllib.request


def create_order(base_url: str, request_id: int) -> tuple[bool, float]:
    payload = json.dumps(
        {"item": f"load-item-{request_id % 10}", "quantity": random.randint(1, 5)}
    ).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/orders",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
            return response.status == 201, time.perf_counter() - started
    except (urllib.error.URLError, TimeoutError):
        return False, time.perf_counter() - started


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded load generator for the AKS orders lab")
    parser.add_argument("url", help="Storefront base URL")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.requests <= 10000 or not 1 <= args.concurrency <= 200:
        parser.error("requests must be 1-10000 and concurrency must be 1-200")

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(executor.map(lambda i: create_order(args.url, i), range(args.requests)))

    successes = sum(1 for success, _ in results if success)
    latencies = sorted(latency for _, latency in results)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
    print(json.dumps({"requests": len(results), "successes": successes, "p95Seconds": round(p95, 3)}))
    raise SystemExit(0 if successes == len(results) else 1)


if __name__ == "__main__":
    main()
