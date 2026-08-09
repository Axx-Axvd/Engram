"""Build or retrieve an approved Engram Context Package through the public API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _request(url: str, *, body: dict | None = None) -> dict:
    payload = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"Engram API returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach Engram API: {exc.reason}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or retrieve a reproducible Engram Context Package."
    )
    parser.add_argument(
        "--api", default="http://localhost:8000", help="Engram API base URL"
    )
    parser.add_argument("--project", required=True, help="Project UUID")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--analysis", help="Approved impact-analysis UUID to package")
    target.add_argument("--package", help="Existing Context Package UUID to retrieve")
    parser.add_argument("--budget", type=int, default=4000, help="Hard token budget")
    parser.add_argument("--created-by", default="cli")
    return parser


def main() -> int:
    args = _parser().parse_args()
    base = args.api.rstrip("/")
    if args.analysis:
        url = (
            f"{base}/api/projects/{args.project}/impact-analyses/"
            f"{args.analysis}/context-packages"
        )
        package = _request(
            url,
            body={"token_budget": args.budget, "created_by": args.created_by},
        )
    else:
        url = f"{base}/api/projects/{args.project}/context-packages/{args.package}"
        package = _request(url)
    json.dump(package, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
