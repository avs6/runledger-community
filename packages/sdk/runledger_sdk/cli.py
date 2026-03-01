"""
RunLedger CLI — ``runledger`` command.

Commands
────────
  validate    Send a synthetic test event and confirm acceptance.
  runs        List recent agent runs for a workspace.
  status      Check API, database, and Redis connectivity.

All commands read ``--api-key`` from the ``RUNLEDGER_API_KEY`` env var if
the flag is not passed explicitly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError as exc:
    raise ImportError(
        "CLI dependencies missing. Install with: pip install runledger-sdk[cli]"
    ) from exc

app = typer.Typer(
    name="runledger",
    help="RunLedger Agent FinOps CLI",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()
err_console = Console(stderr=True, style="bold red")

_DEFAULT_BASE_URL = "https://api.runledger.io"

# ── Common option types ───────────────────────────────────────────────────────

ApiKeyOpt = Annotated[
    str | None,
    typer.Option(
        "--api-key",
        envvar="RUNLEDGER_API_KEY",
        help="RunLedger API key (rl_live_... or rl_test_...)",
    ),
]

BaseUrlOpt = Annotated[
    str,
    typer.Option(
        "--base-url",
        envvar="RUNLEDGER_BASE_URL",
        help="RunLedger API base URL",
    ),
]


def _require_api_key(api_key: str | None) -> str:
    if not api_key:
        err_console.print(
            "API key required. Pass --api-key or set RUNLEDGER_API_KEY env var."
        )
        raise typer.Exit(code=1)
    return api_key


def _client(api_key: str, base_url: str) -> httpx.Client:
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10.0,
    )


# ── validate ──────────────────────────────────────────────────────────────────


@app.command()
def validate(
    api_key: ApiKeyOpt = None,
    base_url: BaseUrlOpt = _DEFAULT_BASE_URL,
) -> None:
    """Send a synthetic test event and confirm the API accepts it."""
    key = _require_api_key(api_key)
    run_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    payload = {
        "event_type": "run_start",
        "run_id": run_id,
        "started_at": now,
        "feature_tag": "runledger-validate",
    }

    console.print(f"[bold]Sending test event[/bold] run_id={run_id[:8]}…")

    try:
        with _client(key, base_url) as client:
            resp = client.post("/ingest/v1/events", json=payload)

        if resp.status_code in (200, 202):
            console.print(f"[green]✓ Accepted[/green]  (HTTP {resp.status_code})")
        else:
            err_console.print(f"✗ Unexpected status {resp.status_code}: {resp.text}")
            raise typer.Exit(code=1)

    except httpx.ConnectError:
        err_console.print(f"✗ Could not connect to {base_url}")
        raise typer.Exit(code=1) from None


# ── runs ──────────────────────────────────────────────────────────────────────


@app.command()
def runs(
    api_key: ApiKeyOpt = None,
    base_url: BaseUrlOpt = _DEFAULT_BASE_URL,
    limit: Annotated[
        int, typer.Option("--limit", "-n", help="Number of runs to show")
    ] = 20,
) -> None:
    """List recent agent runs for this workspace."""
    key = _require_api_key(api_key)

    try:
        with _client(key, base_url) as client:
            resp = client.get("/ingest/v1/runs", params={"limit": limit})
    except httpx.ConnectError:
        err_console.print(f"✗ Could not connect to {base_url}")
        raise typer.Exit(code=1) from None

    if resp.status_code != 200:
        err_console.print(f"✗ API error {resp.status_code}: {resp.text}")
        raise typer.Exit(code=1)

    data: list[dict[str, Any]] = resp.json()

    if not data:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title=f"Recent Runs (last {limit})", show_lines=False)
    table.add_column("Run ID", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Feature", style="dim")
    table.add_column("Cost USD", justify="right")
    table.add_column("Tokens In", justify="right", style="dim")
    table.add_column("Tokens Out", justify="right", style="dim")
    table.add_column("Started", style="dim")

    for run in data:
        status = run.get("status", "—")
        status_str = (
            f"[green]{status}[/green]"
            if status == "succeeded"
            else f"[red]{status}[/red]"
            if status == "failed"
            else f"[yellow]{status}[/yellow]"
        )
        cost = run.get("total_cost_usd")
        cost_str = f"${float(cost):.4f}" if cost else "—"
        in_tok = str(run.get("total_input_tokens") or "—")
        out_tok = str(run.get("total_output_tokens") or "—")
        started = (
            run.get("started_at", "")[:19].replace("T", " ")
            if run.get("started_at")
            else "—"
        )
        run_id_short = str(run.get("id", ""))[:8] + "…"

        table.add_row(
            run_id_short,
            status_str,
            run.get("feature_tag") or "—",
            cost_str,
            in_tok,
            out_tok,
            started,
        )

    console.print(table)


# ── status ────────────────────────────────────────────────────────────────────


@app.command()
def status(
    api_key: ApiKeyOpt = None,
    base_url: BaseUrlOpt = _DEFAULT_BASE_URL,
) -> None:
    """Check API, database, and Redis health."""
    # Health check doesn't require auth
    url = base_url.rstrip("/") + "/health"
    console.print(f"[bold]Checking[/bold] {url} …")

    try:
        resp = httpx.get(url, timeout=5.0)
    except httpx.ConnectError:
        err_console.print(f"✗ Could not connect to {base_url}")
        raise typer.Exit(code=1) from None

    if resp.status_code != 200:
        err_console.print(
            f"✗ Health check failed (HTTP {resp.status_code}): {resp.text}"
        )
        raise typer.Exit(code=1)

    data: dict[str, Any] = resp.json()
    overall = data.get("status", "unknown")
    db = data.get("db", "unknown")
    redis = data.get("redis", "unknown")

    def _fmt(v: str) -> str:
        return f"[green]{v}[/green]" if v == "ok" else f"[red]{v}[/red]"

    console.print(f"  API    {_fmt(overall)}")
    console.print(f"  DB     {_fmt(db)}")
    console.print(f"  Redis  {_fmt(redis)}")

    if overall != "ok" or db != "ok" or redis != "ok":
        raise typer.Exit(code=1)


# ── check-regression ──────────────────────────────────────────────────────────


@app.command(name="check-regression")
def check_regression(
    threshold: Annotated[
        float,
        typer.Option(
            "--threshold", help="Fail if cost regression exceeds this % change"
        ),
    ] = 20.0,
    api_key: ApiKeyOpt = None,
    base_url: BaseUrlOpt = _DEFAULT_BASE_URL,
) -> None:
    """Exit 1 if any workflow cost regression exceeds threshold. Use in GitHub Actions CI gate."""
    key = _require_api_key(api_key)

    try:
        with _client(key, base_url) as client:
            resp = client.get("/analytics/regressions")
    except httpx.ConnectError:
        err_console.print(f"✗ Could not connect to {base_url}")
        raise typer.Exit(code=1) from None

    if resp.status_code != 200:
        err_console.print(f"✗ API error {resp.status_code}: {resp.text}")
        raise typer.Exit(code=1)

    data = resp.json()
    regressions = data.get("items", [])
    failed = [r for r in regressions if float(r.get("change_pct", 0)) > threshold]

    if not failed:
        console.print(
            f"[green]✓ No regressions detected[/green] (threshold: {threshold}%)"
        )
        return

    table = Table(
        title=f"Cost Regressions > {threshold}%",
        show_lines=False,
    )
    table.add_column("Feature", style="cyan")
    table.add_column("Current Avg", justify="right")
    table.add_column("Prior Avg", justify="right")
    table.add_column("Change %", justify="right", style="red")
    table.add_column("Runs", justify="right", style="dim")

    for r in failed:
        change = float(r.get("change_pct", 0))
        table.add_row(
            r.get("feature_tag") or "—",
            f"${float(r.get('current_avg_cost', 0)):.4f}",
            f"${float(r.get('prior_avg_cost', 0)):.4f}",
            f"+{change:.1f}%",
            str(r.get("run_count", "—")),
        )

    console.print(table)
    err_console.print(
        f"✗ {len(failed)} regression(s) exceed {threshold}% threshold — failing CI gate"
    )
    raise typer.Exit(code=1)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
