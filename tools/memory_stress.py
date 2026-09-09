"""Controlled memory-growth workload for the disposable Kali VM demonstration."""

from __future__ import annotations

import argparse
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="Allocate memory gradually, then hold it for observation.")
    parser.add_argument("--total-mb", type=int, default=300, help="maximum allocation (default: 300 MB)")
    parser.add_argument("--step-mb", type=int, default=10, help="allocation per step (default: 10 MB)")
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between steps")
    parser.add_argument("--hold-seconds", type=int, default=60, help="time to retain allocated memory")
    args = parser.parse_args()
    if not 1 <= args.total_mb <= 1024:
        parser.error("--total-mb must be between 1 and 1024")
    if not 1 <= args.step_mb <= args.total_mb:
        parser.error("--step-mb must be between 1 and total-mb")
    if not 0.1 <= args.interval <= 10:
        parser.error("--interval must be between 0.1 and 10 seconds")

    blocks: list[bytearray] = []
    allocated = 0
    print(f"Growing to {args.total_mb} MB in {args.step_mb} MB steps. Press Ctrl+C to stop.")
    while allocated < args.total_mb:
        amount = min(args.step_mb, args.total_mb - allocated)
        block = bytearray(amount * 1024 * 1024)
        block[0] = 1
        blocks.append(block)
        allocated += amount
        print(f"Allocated: {allocated} MB", flush=True)
        time.sleep(args.interval)
    print(f"Holding {allocated} MB for {args.hold_seconds} seconds.", flush=True)
    time.sleep(args.hold_seconds)


if __name__ == "__main__":
    main()
