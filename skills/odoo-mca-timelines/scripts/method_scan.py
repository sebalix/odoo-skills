#!/usr/bin/env python3
"""Scan absent Odoo methods against a target version.

The Odoo MCA does not get method evidence from OpenUpgrade: `apriori.py`
and `upgrade_analysis.txt` never list methods. This script classifies an
absent-method list by comparing normalized method bodies parsed from the
exact MCA scan commits.

Usage:
  python3 method_scan.py \
    --repo /path/to/odoo \
    --module account \
    --source-version 15.0 \
    --target-version 16.0 \
    --source-commit <scan_sha> \
    --target-commit <scan_sha> \
    --absent-methods absent_methods.json \
    --out method_candidates.json

`absent_methods.json` is either a list of `{"model": ..., "name": ...}`
objects or the `code_list_absent_elements` payload `{"elements": [...]}`.

Optional model moves (confirmed MCA model timelines):

  {"old.model": "new.model"}
  {"old.model": {"next_module": "target_module", "next_model": "new.model"}}

Optional scan-commit overrides for target modules:

  {"analytic": {"16.0": "<sha>"}, "stock": {"15.0": "<sha>"}}

Cross-model and cross-module searches:

  --search-all-models                  compare against every model in the
                                       target module (cross-model moves)
  --search-modules stock_account,account
                                       also search base modules for the
                                       same model (extension methods)
  --min-name-ratio 0.5                 flag exact bodies with an unrelated
                                       name as exact_unrelated_name
  --reject-target-existing-in-source   flag a candidate that already exists
                                       as a sibling in the source version

The output contains a summary and the exact/similar/weak candidates. Use
`--include-no-match` to also emit the no_match records for reporting.
"""

from __future__ import annotations

import argparse
import ast
import copy
import difflib
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict

GENERIC = {
    "create",
    "write",
    "unlink",
    "read",
    "search",
    "search_read",
    "name_get",
    "name_search",
    "default_get",
    "fields_get",
    "fields_view_get",
    "init",
    "load",
    "copy",
    "copy_data",
    "mapped",
    "filtered",
    "sorted",
    "update",
}


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)


def git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def ensure_tree(repo: str, module: str, version: str, commit: str, base: str) -> str:
    """Extract `addons/<module>` at `commit` and return the extraction root."""
    safe_commit = commit.replace("/", "_").replace(":", "_")
    dest = os.path.join(base, module, version, safe_commit)
    marker = os.path.join(dest, ".done")
    if os.path.exists(marker):
        return dest
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    eprint(f"extract {module} {version} {commit}")
    archive = subprocess.Popen(
        ["git", "-C", repo, "archive", commit, f"addons/{module}"],
        stdout=subprocess.PIPE,
    )
    tar = subprocess.Popen(["tar", "-x", "-C", dest], stdin=archive.stdout)
    if archive.stdout:
        archive.stdout.close()
    tar.communicate()
    if archive.wait() != 0 or tar.returncode != 0:
        raise RuntimeError(f"cannot extract {module} at {commit}")
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write("ok")
    return dest


def parse_tree(
    repo: str,
    module: str,
    version: str,
    commit: str,
    base: str,
    cache: str,
) -> dict[tuple[str, str], list[dict]]:
    """Return {(model, method_name): [definition, ...]} for one module tree."""
    safe_commit = commit.replace("/", "_").replace(":", "_")
    # v2 adds the `owned` flag (True when the class declares _name).
    cache_file = os.path.join(cache, f"{module}__{version}__{safe_commit}__v2.json")
    if os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as handle:
            raw = json.load(handle)
        return {(model, name): defs for model, name, defs in raw}

    root = ensure_tree(repo, module, version, commit, base)
    eprint(f"parse {module} {version}")
    result: dict[tuple[str, str], list[dict]] = defaultdict(list)

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in ("tests", "i18n", "static", "__pycache__")
        ]
        for filename in filenames:
            if not filename.endswith(".py") or filename == "__init__.py":
                continue
            path = os.path.join(dirpath, filename)
            relpath = os.path.relpath(path, root)
            try:
                with open(path, encoding="utf-8") as handle:
                    source = handle.read()
                tree = ast.parse(source)
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            for cls in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
                model_name = None
                inherit: list[str] = []
                for statement in cls.body:
                    if not (
                        isinstance(statement, ast.Assign)
                        and len(statement.targets) == 1
                        and isinstance(statement.targets[0], ast.Name)
                    ):
                        continue
                    key = statement.targets[0].id
                    if key not in ("_name", "_inherit"):
                        continue
                    try:
                        value = ast.literal_eval(statement.value)
                    except (ValueError, TypeError):
                        continue
                    if key == "_name":
                        model_name = value
                    else:
                        inherit = [value] if isinstance(value, str) else list(value)
                models = [model_name] if model_name else inherit
                if not models:
                    continue
                for function in cls.body:
                    if not isinstance(
                        function, (ast.FunctionDef, ast.AsyncFunctionDef)
                    ):
                        continue
                    copy_function = copy.deepcopy(function)
                    copy_function.name = "<NAME>"
                    try:
                        body = ast.unparse(copy_function)
                        args = ast.unparse(function.args)
                    except Exception:
                        continue
                    body = "\n".join(line.rstrip() for line in body.splitlines())
                    for model in models:
                        result[(model, function.name)].append(
                            {
                                "file": relpath,
                                "line": function.lineno,
                                "body": body,
                                "args": args,
                                "owned": model_name is not None,
                            }
                        )

    raw = [[model, name, defs] for (model, name), defs in result.items()]
    with open(cache_file, "w", encoding="utf-8") as handle:
        json.dump(raw, handle)
    return result


def ratio(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, left, right).ratio()


def load_absent(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    elements = payload["elements"] if isinstance(payload, dict) else payload
    methods = []
    for element in elements:
        if element.get("element_type") not in (None, "method"):
            continue
        methods.append(
            {
                "model": element["model"],
                "name": element["name"],
            }
        )
    return methods


def load_json(path: str | None) -> dict:
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def resolve_model(model_map: dict, source_model: str) -> tuple[str, str]:
    value = model_map.get(source_model)
    if not value:
        return "", source_model
    if isinstance(value, str):
        return "", value
    return value.get("next_module", ""), value.get("next_model", source_model)


def source_url(
    github_repo: str,
    ref: str,
    path: str,
    line: int,
    enabled: bool,
) -> str | None:
    if not enabled:
        return None
    return f"https://github.com/{github_repo}/blob/{ref}/{path}#L{line}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify absent Odoo methods against a target version."
    )
    parser.add_argument("--repo", required=True, help="Odoo git clone")
    parser.add_argument("--module", required=True, help="Source technical module")
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--target-version", required=True)
    parser.add_argument(
        "--source-commit",
        help="Exact source scan commit (default: source version ref)",
    )
    parser.add_argument(
        "--target-commit",
        help="Exact target scan commit (default: target version ref)",
    )
    parser.add_argument(
        "--absent-methods",
        required=True,
        help="JSON list or code_list_absent_elements payload",
    )
    parser.add_argument("--model-map", help="Optional model rename map JSON")
    parser.add_argument(
        "--commits",
        help="Optional JSON {module: {version: commit}} for cross-module targets",
    )
    parser.add_argument(
        "--search-modules",
        help=(
            "Comma-separated extra target modules to search for the same "
            "model/name (e.g. 'stock_account,account')"
        ),
    )
    parser.add_argument(
        "--search-all-models",
        action="store_true",
        help="Also compare against other models in the target module(s)",
    )
    parser.add_argument(
        "--min-name-ratio",
        type=float,
        default=0.0,
        help=(
            "For an exact body, require this minimum name similarity; "
            "below it the status becomes exact_unrelated_name"
        ),
    )
    parser.add_argument(
        "--reject-target-existing-in-source",
        action="store_true",
        help=(
            "Report an exact candidate whose name already exists in the "
            "source version as target_exists_in_source"
        ),
    )
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-ratio", type=float, default=0.92)
    parser.add_argument("--weak-ratio", type=float, default=0.80)
    parser.add_argument(
        "--include-weak",
        action="store_true",
        help="Emit weak candidates (>= weak-ratio, < min-ratio)",
    )
    parser.add_argument(
        "--include-no-match",
        action="store_true",
        help="Emit no_match records too",
    )
    parser.add_argument(
        "--cache-dir",
        default="/tmp/odoo-mca-method-cache",
        help="Writable cache for extracted trees and parses",
    )
    parser.add_argument(
        "--github-repo",
        default="odoo/odoo",
        help="GitHub repository for source URLs (default: odoo/odoo)",
    )
    parser.add_argument(
        "--target-ref",
        help="Ref used in source URLs (default: target commit/version)",
    )
    parser.add_argument("--no-url", action="store_true", help="Do not emit URLs")
    args = parser.parse_args()

    trees = os.path.join(args.cache_dir, "trees")
    cache = os.path.join(args.cache_dir, "parse")
    os.makedirs(trees, exist_ok=True)
    os.makedirs(cache, exist_ok=True)

    source_commit = args.source_commit or args.source_version
    target_commit = args.target_commit or args.target_version
    commits = load_json(args.commits)
    model_map = load_json(args.model_map)
    methods = load_absent(args.absent_methods)

    parsed: dict[tuple[str, str, str], dict] = {}

    def get_parsed(module: str, version: str, commit: str) -> dict:
        key = (module, version, commit)
        if key not in parsed:
            parsed[key] = parse_tree(
                args.repo, module, version, commit, trees, cache
            )
        return parsed[key]

    source = get_parsed(args.module, args.source_version, source_commit)
    summary: dict[str, int] = defaultdict(int)
    records = []

    extra_modules = [
        item.strip()
        for item in (args.search_modules or "").split(",")
        if item.strip()
    ]

    for method in methods:
        model = method["model"]
        name = method["name"]
        source_defs = source.get((model, name), [])
        if not source_defs:
            summary["source_not_parsed"] += 1
            continue

        target_module, target_model = resolve_model(model_map, model)
        target_module = target_module or args.module
        if target_module == args.module:
            target_commit_for_module = target_commit
        else:
            target_commit_for_module = (
                commits.get(target_module, {}).get(args.target_version)
                or args.target_version
            )
        target = get_parsed(
            target_module, args.target_version, target_commit_for_module
        )

        same = target.get((target_model, name), [])
        if same:
            summary["same_name_exists"] += 1
            records.append(
                {
                    "module": args.module,
                    "version": args.source_version,
                    "model": model,
                    "name": name,
                    "target_module": target_module,
                    "target_model": target_model,
                    "status": "same_name_exists",
                    "target": [
                        {"file": item["file"], "line": item["line"]}
                        for item in same[:3]
                    ],
                }
            )
            continue

        target_contexts = [(target_module, target)]
        for extra_module in extra_modules:
            if extra_module == target_module:
                continue
            extra_commit = (
                commits.get(extra_module, {}).get(args.target_version)
                or args.target_version
            )
            target_contexts.append(
                (
                    extra_module,
                    get_parsed(extra_module, args.target_version, extra_commit),
                )
            )
        context_models = [
            (module, parsed_module, {key[0] for key in parsed_module})
            for module, parsed_module in target_contexts
        ]

        if not any(target_model in models for _, _, models in context_models):
            status = (
                "extension_model_removed"
                if all(not item.get("owned", True) for item in source_defs)
                else "model_removed"
            )
            summary[status] += 1
            records.append(
                {
                    "module": args.module,
                    "version": args.source_version,
                    "model": model,
                    "name": name,
                    "target_module": target_module,
                    "target_model": target_model,
                    "status": status,
                }
            )
            continue

        candidates = []
        for candidate_module, parsed_module, _ in context_models:
            for (candidate_model, candidate_name), definitions in parsed_module.items():
                if candidate_model != target_model and not args.search_all_models:
                    continue
                for definition in definitions:
                    best_body = 0.0
                    best_args = 0.0
                    best_source = None
                    for source_definition in source_defs:
                        body_ratio = ratio(
                            source_definition["body"], definition["body"]
                        )
                        args_ratio = ratio(
                            source_definition["args"], definition["args"]
                        )
                        if body_ratio > best_body or (
                            body_ratio == best_body and args_ratio > best_args
                        ):
                            best_body = body_ratio
                            best_args = args_ratio
                            best_source = source_definition
                    candidate_commit = (
                        target_commit_for_module
                        if candidate_module == target_module
                        else (
                            commits.get(candidate_module, {}).get(
                                args.target_version
                            )
                            or args.target_version
                        )
                    )
                    candidates.append(
                        {
                            "candidate_module": candidate_module,
                            "candidate_model": candidate_model,
                            "target_name": candidate_name,
                            "target_file": definition["file"],
                            "target_line": definition["line"],
                            "target_args": definition["args"],
                            "body_ratio": round(best_body, 4),
                            "args_ratio": round(best_args, 4),
                            "name_ratio": round(ratio(name, candidate_name), 4),
                            "source_file": best_source["file"]
                            if best_source
                            else None,
                            "source_line": best_source["line"]
                            if best_source
                            else None,
                            "target_url": source_url(
                                args.github_repo,
                                args.target_ref or candidate_commit,
                                definition["file"],
                                definition["line"],
                                not args.no_url,
                            ),
                        }
                    )

        candidates.sort(
            key=lambda item: (item["body_ratio"], item["name_ratio"]),
            reverse=True,
        )
        top = candidates[:3]
        if not top:
            summary["no_candidate"] += 1
            continue

        best = top[0]
        exact_targets = {
            (
                candidate["candidate_module"],
                candidate["candidate_model"],
                candidate["target_name"],
            )
            for candidate in candidates
            if candidate["body_ratio"] >= 0.999
        }
        if len(exact_targets) > 1:
            status = "ambiguous"
        elif best["body_ratio"] >= 0.999:
            if args.min_name_ratio and best["name_ratio"] < args.min_name_ratio:
                status = "exact_unrelated_name"
            elif args.reject_target_existing_in_source and (
                best["candidate_model"], best["target_name"]
            ) in source:
                status = "target_exists_in_source"
            else:
                status = "exact"
        elif best["body_ratio"] >= args.min_ratio:
            status = "similar"
        elif best["body_ratio"] >= args.weak_ratio:
            status = "weak"
        else:
            status = "no_match"

        summary[status] += 1
        if status == "no_match" and not args.include_no_match:
            continue
        if status == "weak" and not args.include_weak:
            continue
        records.append(
            {
                "module": args.module,
                "version": args.source_version,
                "model": model,
                "name": name,
                "target_module": target_module,
                "target_model": target_model,
                "best_target_module": best["candidate_module"],
                "best_target_model": best["candidate_model"],
                "cross_model": best["candidate_model"] != target_model,
                "cross_module": best["candidate_module"] != target_module,
                "generic_name": name in GENERIC,
                "status": status,
                "candidates": top,
            }
        )

    output = {
        "module": args.module,
        "source_version": args.source_version,
        "target_version": args.target_version,
        "source_commit": source_commit,
        "target_commit": target_commit,
        "min_ratio": args.min_ratio,
        "summary": dict(sorted(summary.items())),
        "candidates": records,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=1)
    eprint(json.dumps(output["summary"], indent=2))
    eprint(f"written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
