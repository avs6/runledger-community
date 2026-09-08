#!/usr/bin/env python3
"""
Master runner for all RunLedger demo operations.

Single entry point for the entire demo lifecycle:

  ── Setup & Seed ──────────────────────────────────────────────
    python scripts/run_demo.py scenario          # print canonical scenario
    python scripts/run_demo.py cleanup            # truncate data (preserves admin + pricing)
    python scripts/run_demo.py cleanup --hard     # wipe ALL volumes
    python scripts/run_demo.py seed-demo          # REST demo seed (quick, ~30s)
    python scripts/run_demo.py full-simulate      # full cluster simulation
    python scripts/run_demo.py all                # cleanup → seed-demo
    python scripts/run_demo.py all --full         # cleanup → full-simulate

  ── Traffic & Agents ──────────────────────────────────────────
    python scripts/run_demo.py traffic            # generate agent traffic (batch mode)
    python scripts/run_demo.py traffic --continuous  # continuous traffic loop
    python scripts/run_demo.py otlp-traffic       # generate OTLP trace traffic

  ── Gateway & Bench ───────────────────────────────────────────
    python scripts/run_demo.py bench              # run gateway benchmark
    python scripts/run_demo.py bench-report       # print benchmark report

  ── Integrations ──────────────────────────────────────────────
    python scripts/run_demo.py localai            # bootstrap LocalAI Agent Stack org
    python scripts/run_demo.py localai --inject   # also inject MCP configs into Claude/Codex
    python scripts/run_demo.py mcp-validate       # validate MCP endpoint connectivity
    python scripts/run_demo.py kafka              # consume Kafka/Redpanda events
    python scripts/run_demo.py backup             # S3 backup
    python scripts/run_demo.py backup --restore   # S3 restore

  ── Info ──────────────────────────────────────────────────────
    python scripts/run_demo.py labs               # print labs workbook path
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
CORE_DIR = SCRIPT_ROOT / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from demo_scenario import scenario_lines

LABS_README = SCRIPT_ROOT / "labs" / "README.md"


def _run_script(script: Path, passthrough: list[str] | None = None) -> int:
    cmd = [sys.executable, str(script), *(passthrough or [])]
    completed = subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    return completed.returncode


def _banner(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


# ── Setup & Seed ──────────────────────────────────────────────────────────────

def cmd_scenario(_args: argparse.Namespace) -> int:
    print("\n".join(scenario_lines()))
    return 0


def cmd_labs(_args: argparse.Namespace) -> int:
    print("\n".join(scenario_lines()))
    print("")
    print(f"Labs workbook: {LABS_README}")
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    passthrough = []
    if getattr(args, "hard", False):
        passthrough.append("--hard")
    if getattr(args, "base_url", None):
        passthrough.extend(["--base-url", args.base_url])
    return _run_script(CORE_DIR / "cleanup.py", passthrough)


def cmd_seed_demo(args: argparse.Namespace) -> int:
    return _run_script(CORE_DIR / "seed_demo.py", getattr(args, "args", []))


def cmd_full_simulate(args: argparse.Namespace) -> int:
    return _run_script(CORE_DIR / "full_simulate.py", getattr(args, "args", []))


def cmd_all(args: argparse.Namespace) -> int:
    _banner("Step 1/2: Cleanup")
    cleanup_args = ["--hard"] if getattr(args, "hard", False) else []
    rc = _run_script(CORE_DIR / "cleanup.py", cleanup_args)
    if rc != 0:
        print(f"\nCleanup failed (exit {rc}). Aborting.")
        return rc

    if getattr(args, "full", False):
        _banner("Step 2/2: Full Simulate")
        rc = _run_script(CORE_DIR / "full_simulate.py", getattr(args, "args", []))
    else:
        _banner("Step 2/2: Seed Demo")
        rc = _run_script(CORE_DIR / "seed_demo.py")
    if rc != 0:
        print(f"\nSeed/simulate failed (exit {rc}).")
    return rc


# ── Traffic & Agents ──────────────────────────────────────────────────────────

def cmd_traffic(args: argparse.Namespace) -> int:
    passthrough = []
    if args.state_file:
        passthrough.extend(["--state-file", args.state_file])
    if args.base_url:
        passthrough.extend(["--base-url", args.base_url])
    if args.workspace:
        passthrough.extend(["--workspace", args.workspace])
    if args.source:
        passthrough.extend(["--source", args.source])
    if args.continuous:
        passthrough.extend(["--batches", "999999", "--sleep", str(args.sleep)])
    else:
        passthrough.extend(["--batches", str(args.batches)])
        passthrough.extend(["--sleep", str(args.sleep)])
    passthrough.extend(["--batch-size", str(args.batch_size)])
    return _run_script(SCRIPT_ROOT / "localai" / "generate_agent_traffic.py", passthrough)


def cmd_otlp_traffic(args: argparse.Namespace) -> int:
    passthrough = []
    if args.state_file:
        passthrough.extend(["--state-file", args.state_file])
    if args.base_url:
        passthrough.extend(["--base-url", args.base_url])
    if args.workspace:
        passthrough.extend(["--workspace", args.workspace])
    if args.source:
        passthrough.extend(["--source", args.source])
    passthrough.extend(["--batches", str(args.batches)])
    passthrough.extend(["--traces", str(args.traces)])
    return _run_script(SCRIPT_ROOT / "localai" / "generate_otlp_traffic.py", passthrough)


# ── Gateway & Bench ───────────────────────────────────────────────────────────

def cmd_bench(args: argparse.Namespace) -> int:
    passthrough = ["--api-key", args.api_key, "--alias", args.alias]
    if args.base_url:
        passthrough.extend(["--base-url", args.base_url])
    passthrough.extend(["--repeat", str(args.repeat)])
    passthrough.extend(["--concurrency", str(args.concurrency)])
    if args.cache:
        passthrough.append("--cache")
    if args.semantic_cache:
        passthrough.append("--semantic-cache")
    if args.context_compiler:
        passthrough.append("--context-compiler")
    if args.provider_url:
        passthrough.extend(["--provider-url", args.provider_url])
    if args.provider_model:
        passthrough.extend(["--provider-model", args.provider_model])
    if args.provider_auth_value:
        passthrough.extend(["--provider-auth-value", args.provider_auth_value])
    return _run_script(SCRIPT_ROOT / "bench" / "run_benchmark.py", passthrough)


def cmd_bench_report(args: argparse.Namespace) -> int:
    passthrough = ["--api-key", args.api_key]
    if args.base_url:
        passthrough.extend(["--base-url", args.base_url])
    passthrough.extend(["--days", str(args.days)])
    if args.alias:
        passthrough.extend(["--alias", args.alias])
    return _run_script(SCRIPT_ROOT / "bench" / "report.py", passthrough)


# ── Integrations ──────────────────────────────────────────────────────────────

def cmd_localai(args: argparse.Namespace) -> int:
    passthrough = []
    if args.base_url:
        passthrough.extend(["--base-url", args.base_url])
    if args.rotate_keys:
        passthrough.append("--rotate-keys")
    rc = _run_script(SCRIPT_ROOT / "localai" / "bootstrap_runledger_org.py", passthrough)
    if rc != 0:
        return rc
    if args.inject:
        _banner("Injecting MCP configs into Claude Desktop and Codex")
        rc = _run_script(SCRIPT_ROOT / "localai" / "inject_mcp_configs.py")
    return rc


def cmd_mcp_validate(args: argparse.Namespace) -> int:
    passthrough = []
    if args.endpoint:
        passthrough.extend(["--endpoint", args.endpoint])
    if args.api_key:
        passthrough.extend(["--api-key", args.api_key])
    return _run_script(SCRIPT_ROOT / "mcp" / "validate_mcp_connection.py", passthrough)


def cmd_kafka(args: argparse.Namespace) -> int:
    passthrough = []
    if args.topic:
        passthrough.extend(["--topic", args.topic])
    if args.container:
        passthrough.extend(["--container", args.container])
    passthrough.extend(["--offset", args.offset])
    return _run_script(SCRIPT_ROOT / "labs" / "kafka_consumer.py", passthrough)


def cmd_backup(args: argparse.Namespace) -> int:
    if args.restore:
        action = "restore"
        passthrough = [action]
        if args.confirm:
            passthrough.append("--confirm-restore")
        else:
            print("Restore is destructive. Re-run with: run_demo.py backup --restore --confirm")
            return 1
    elif args.list:
        passthrough = ["list"]
    else:
        passthrough = ["backup"]
    if args.bucket:
        passthrough.extend(["--bucket", args.bucket])
    return _run_script(SCRIPT_ROOT / "localai" / "localai_s3_backup.py", passthrough)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Master runner for all RunLedger demo operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── Setup & Seed ──
    sub.add_parser("scenario", help="Print the canonical org/user/workspace scenario.")

    sub.add_parser("labs", help="Print the labs workbook path and scenario.")

    p = sub.add_parser("cleanup", help="Reset the stack to a blank slate.")
    p.add_argument("--hard", action="store_true", help="Wipe ALL volumes (docker compose down -v).")
    p.add_argument("--base-url", default="http://localhost:8201")

    p = sub.add_parser("seed-demo", help="Run the REST demo seed (~30s).")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p = sub.add_parser("full-simulate", help="Run the full cluster simulator.")
    p.add_argument("args", nargs=argparse.REMAINDER)

    p = sub.add_parser("all", help="Full pipeline: cleanup → seed.")
    p.add_argument("--full", action="store_true", help="Use full-simulate instead of seed-demo.")
    p.add_argument("--hard", action="store_true", help="Use hard cleanup (wipe volumes).")
    p.add_argument("args", nargs=argparse.REMAINDER)

    # ── Traffic & Agents ──
    p = sub.add_parser("traffic", help="Generate agent traffic into a workspace.")
    p.add_argument("--continuous", action="store_true", help="Run indefinitely (Ctrl+C to stop).")
    p.add_argument("--workspace", default="PythonAgents")
    p.add_argument("--source", default="python-agents")
    p.add_argument("--batches", type=int, default=12)
    p.add_argument("--batch-size", type=int, default=25)
    p.add_argument("--sleep", type=float, default=2.0, help="Seconds between batches.")
    p.add_argument("--state-file", default=None)
    p.add_argument("--base-url", default=None)

    p = sub.add_parser("otlp-traffic", help="Generate OTLP trace traffic into a workspace.")
    p.add_argument("--workspace", default="OpenWebUI")
    p.add_argument("--source", default="localai-otlp")
    p.add_argument("--batches", type=int, default=2)
    p.add_argument("--traces", type=int, default=40)
    p.add_argument("--state-file", default=None)
    p.add_argument("--base-url", default=None)

    # ── Gateway & Bench ──
    p = sub.add_parser("bench", help="Run gateway benchmark.")
    p.add_argument("--api-key", required=True)
    p.add_argument("--alias", required=True, help="Gateway alias to target.")
    p.add_argument("--base-url", default="http://localhost:8201")
    p.add_argument("--repeat", type=int, default=30)
    p.add_argument("--concurrency", type=int, default=5)
    p.add_argument("--cache", action="store_true")
    p.add_argument("--semantic-cache", action="store_true")
    p.add_argument("--context-compiler", action="store_true")
    p.add_argument("--provider-url", default=None, help="Direct provider comparison URL.")
    p.add_argument("--provider-model", default=None)
    p.add_argument("--provider-auth-value", default=None)

    p = sub.add_parser("bench-report", help="Print gateway benchmark report.")
    p.add_argument("--api-key", required=True)
    p.add_argument("--base-url", default="http://localhost:8201")
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--alias", default=None)

    # ── Integrations ──
    p = sub.add_parser("localai", help="Bootstrap LocalAI Agent Stack org and workspaces.")
    p.add_argument("--inject", action="store_true", help="Also inject MCP configs into Claude/Codex.")
    p.add_argument("--rotate-keys", action="store_true", help="Mint fresh API keys.")
    p.add_argument("--base-url", default=None)

    p = sub.add_parser("mcp-validate", help="Validate MCP endpoint connectivity and tools.")
    p.add_argument("--endpoint", default=None)
    p.add_argument("--api-key", default=None)

    p = sub.add_parser("kafka", help="Consume events from local Redpanda/Kafka.")
    p.add_argument("--topic", default=None)
    p.add_argument("--container", default=None)
    p.add_argument("--offset", choices=("start", "end"), default="end")

    p = sub.add_parser("backup", help="S3-compatible backup and restore.")
    p.add_argument("--restore", action="store_true", help="Restore instead of backup.")
    p.add_argument("--list", action="store_true", help="List existing backups.")
    p.add_argument("--confirm", action="store_true", help="Confirm destructive restore.")
    p.add_argument("--bucket", default=None)

    args = parser.parse_args()

    dispatch = {
        "scenario": cmd_scenario,
        "labs": cmd_labs,
        "cleanup": cmd_cleanup,
        "seed-demo": cmd_seed_demo,
        "full-simulate": cmd_full_simulate,
        "all": cmd_all,
        "traffic": cmd_traffic,
        "otlp-traffic": cmd_otlp_traffic,
        "bench": cmd_bench,
        "bench-report": cmd_bench_report,
        "localai": cmd_localai,
        "mcp-validate": cmd_mcp_validate,
        "kafka": cmd_kafka,
        "backup": cmd_backup,
    }
    handler = dispatch.get(args.command)
    if handler:
        return handler(args)

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
