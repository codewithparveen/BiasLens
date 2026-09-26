"""Command-line interface: ``biaslens estimate | audit | report | cache-stats``.

Stdlib argparse only -- no extra CLI framework dependency. Every subcommand
prints machine-readable JSON to stdout by default (so it composes with
``jq``/pipelines) and a human summary to stderr, except where noted.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .auditor import Auditor
from .exceptions import BiasLensError
from .report import AuditReport


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _add_plan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--queries", required=True, help="Comma-separated queries.")
    parser.add_argument("--cities", required=True, help="Comma-separated cities.")
    parser.add_argument(
        "--languages", required=True, help="Comma-separated language codes (hl), e.g. ta,hi,en."
    )
    parser.add_argument("--runs", type=int, default=2, help="Reliability runs per variant (default 2).")
    parser.add_argument(
        "--max-credits", type=int, default=None, help="Refuse to exceed this many SerpApi credits."
    )


def cmd_estimate(args: argparse.Namespace) -> int:
    auditor = Auditor(api_key=None, cache=None)
    result = auditor.estimate(
        queries=_split_csv(args.queries),
        cities=_split_csv(args.cities),
        languages=_split_csv(args.languages),
        runs_per_variant=args.runs,
        max_credits=args.max_credits,
    )
    print(result.model_dump_json(indent=2))
    print(
        f"\nEstimated: {result.budget.total_credits} credits "
        f"({result.budget.search_calls} search + {result.budget.trends_calls} trends). "
        f"Within budget: {result.budget.within_budget}",
        file=sys.stderr,
    )
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    auditor = Auditor(api_key=args.api_key, cache="sqlite", cache_path=args.cache_path)
    try:
        report = auditor.audit(
            queries=_split_csv(args.queries),
            cities=_split_csv(args.cities),
            languages=_split_csv(args.languages),
            runs_per_variant=args.runs,
            max_credits=args.max_credits,
            override=args.override,
        )
    except BiasLensError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"hint: {exc.hint}", file=sys.stderr)
        return 1
    finally:
        auditor.close()

    output = report.to_json()
    if args.output:
        Path(args.output).write_text(output)
        print(f"Wrote report to {args.output}", file=sys.stderr)
    else:
        print(output)
    summary = report.summary()
    print(f"\nAverage inequality score: {summary['average_inequality_score']}/100", file=sys.stderr)
    print(f"Credits used: {summary['credits_used']}", file=sys.stderr)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    path = Path(args.report_path)
    if not path.exists():
        print(f"error: no such file: {path}", file=sys.stderr)
        return 1
    report = AuditReport.model_validate_json(path.read_text())
    if args.format == "html":
        print(report.to_html())
    elif args.format == "summary":
        print(json.dumps(report.summary(), indent=2))
    else:
        print(report.to_json())
    return 0


def cmd_cache_stats(args: argparse.Namespace) -> int:
    auditor = Auditor(api_key=None, cache="sqlite", cache_path=args.cache_path)
    stats = auditor.cache_stats()
    auditor.close()
    print(json.dumps(stats, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biaslens", description="Audit search-result bias across India.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_estimate = sub.add_parser("estimate", help="Show the credit cost of a plan without spending anything.")
    _add_plan_args(p_estimate)
    p_estimate.set_defaults(func=cmd_estimate)

    p_audit = sub.add_parser("audit", help="Run a real audit against SerpApi.")
    _add_plan_args(p_audit)
    p_audit.add_argument("--api-key", default=None, help="SerpApi key (falls back to SERPAPI_KEY / .env).")
    p_audit.add_argument("--cache-path", default="biaslens_cache.sqlite3", help="SQLite cache file path.")
    p_audit.add_argument("--override", action="store_true", help="Proceed even if over max-credits.")
    p_audit.add_argument(
        "--output", default=None, help="Write the report JSON to this file instead of stdout."
    )
    p_audit.set_defaults(func=cmd_audit)

    p_report = sub.add_parser("report", help="Render a saved report as json, html, or a short summary.")
    p_report.add_argument("report_path", help="Path to a report JSON file produced by `biaslens audit`.")
    p_report.add_argument("--format", choices=["json", "html", "summary"], default="summary")
    p_report.set_defaults(func=cmd_report)

    p_cache = sub.add_parser("cache-stats", help="Show SQLite cache hit/expiry stats.")
    p_cache.add_argument("--cache-path", default="biaslens_cache.sqlite3")
    p_cache.set_defaults(func=cmd_cache_stats)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
