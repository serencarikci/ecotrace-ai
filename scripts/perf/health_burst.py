#!/usr/bin/env python3
from __future__ import annotations
import argparse
import concurrent.futures
import time
import urllib.request

def one(url: str) -> int:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.status

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000/health')
    parser.add_argument('--concurrency', type=int, default=100)
    args = parser.parse_args()
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(one, [args.url] * args.concurrency))
    elapsed = time.perf_counter() - start
    ok = sum((1 for s in results if s == 200))
    print(f'ok={ok}/{len(results)} elapsed_s={elapsed:.3f}')
if __name__ == '__main__':
    main()
