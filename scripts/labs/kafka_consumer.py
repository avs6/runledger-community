#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consume RunLedger events from the local Redpanda demo container."
    )
    parser.add_argument("--topic", default="runledger.events")
    parser.add_argument("--container", default="runledger-redpanda")
    parser.add_argument("--offset", choices=("start", "end"), default="end")
    parser.add_argument("--format", default="%v")
    args = parser.parse_args()

    command = [
        "docker",
        "exec",
        "-i",
        args.container,
        "rpk",
        "topic",
        "consume",
        args.topic,
        "--brokers=localhost:9092",
        f"--offset={args.offset}",
        f"--format={args.format}",
    ]
    print(" ".join(command))
    try:
        return subprocess.call(command)
    except FileNotFoundError:
        print("docker is required for the local Redpanda consumer helper", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
