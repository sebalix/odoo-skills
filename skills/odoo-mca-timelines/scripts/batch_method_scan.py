#!/usr/bin/env python3
"""Run method_scan.py for several module/version transitions.

Example config:

{
  "repo": "/path/to/odoo",
  "scan_commits": {
    "project": {"14.0": "<sha>", "15.0": "<sha>"}
  },
  "transitions": [
    {"module": "project", "source": "14.0", "target": "15.0",
     "absent": "/tmp/absent_methods/project_14.0.json"},
    {"module": "sale_project", "source": "14.0", "target": "15.0",
     "absent": "/tmp/absent_methods/sale_project_14.0.json"}
  ],
  "out_dir": "/tmp/method_candidates",
  "search_all_models": true,
  "search_modules": ["stock_account", "account"],
  "min_name_ratio": 0.5,
  "flag_target_existing_in_source": true,
  "include_weak": false,
  "include_no_match": false
}

Each transition may override `out`, `search_all_models`, `search_modules`,
`min_name_ratio`, `flag_target_existing_in_source`, `include_weak`, and
`include_no_match`. The old `reject_target_existing_in_source` key is
accepted as an alias. The merged output is written to
`<out_dir>/batch_summary.json`.

For a large module (base, mail) run the batch in the background or per
transition: each transition writes its own JSON. A missing output file or
a missing summary is treated as a failure, not silently as an empty
transition.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(HERE, "method_scan.py")


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def commit_for(config: dict, module: str, version: str) -> str:
    value = (
        config.get("scan_commits", {})
        .get(module, {})
        .get(version)
    )
    if not value:
        raise SystemExit(
            f"missing scan_commits[{module!r}][{version!r}] in the config"
        )
    return value


def build_command(
    config: dict,
    transition: dict,
    out_path: str,
) -> list[str]:
    module = transition["module"]
    source = transition["source"]
    target = transition["target"]
    command = [
        sys.executable,
        SCANNER,
        "--repo",
        config["repo"],
        "--module",
        module,
        "--source-version",
        source,
        "--target-version",
        target,
        "--source-commit",
        transition.get("source_commit")
        or commit_for(config, module, source),
        "--target-commit",
        transition.get("target_commit")
        or commit_for(config, module, target),
        "--absent-methods",
        transition["absent"],
        "--out",
        out_path,
        "--cache-dir",
        config.get("cache_dir", "/tmp/odoo-mca-method-cache"),
    ]
    flags = {
        "search_all_models": "--search-all-models",
        "flag_target_existing_in_source": "--flag-target-existing-in-source",
        "include_weak": "--include-weak",
        "include_no_match": "--include-no-match",
    }
    for key, flag in flags.items():
        value = transition.get(key, config.get(key, False))
        if key == "flag_target_existing_in_source":
            value = value or transition.get(
                "reject_target_existing_in_source",
                config.get("reject_target_existing_in_source", False),
            )
        if value:
            command.append(flag)
    name_ratio = transition.get(
        "min_name_ratio", config.get("min_name_ratio")
    )
    if name_ratio is not None:
        command.extend(["--min-name-ratio", str(name_ratio)])
    search_modules = transition.get(
        "search_modules", config.get("search_modules")
    )
    if search_modules:
        if isinstance(search_modules, str):
            search_modules = [search_modules]
        command.extend(["--search-modules", ",".join(search_modules)])
    commits_path = config.get("commits")
    if commits_path:
        command.extend(["--commits", commits_path])
    model_map = transition.get("model_map", config.get("model_map"))
    if model_map:
        command.extend(["--model-map", model_map])
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run method_scan.py over several transitions."
    )
    parser.add_argument("--config", required=True, help="Batch JSON config")
    args = parser.parse_args()

    config = load_json(args.config)
    out_dir = config.get("out_dir", "/tmp/method_candidates")
    os.makedirs(out_dir, exist_ok=True)

    total = Counter()
    results = []
    failures = 0
    for index, transition in enumerate(config.get("transitions", []), start=1):
        module = transition["module"]
        source = transition["source"]
        target = transition["target"]
        out_path = transition.get("out") or os.path.join(
            out_dir, f"{module}_{source}_{target}.json"
        )
        command = build_command(config, transition, out_path)
        print(
            f"[{index}] {module} {source}->{target}",
            file=sys.stderr,
            flush=True,
        )
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            failures += 1
            results.append(
                {
                    "module": module,
                    "source": source,
                    "target": target,
                    "error": completed.stderr.strip()[-2000:],
                }
            )
            continue
        if not os.path.exists(out_path):
            failures += 1
            results.append(
                {
                    "module": module,
                    "source": source,
                    "target": target,
                    "error": "scanner produced no output file",
                }
            )
            continue
        output = load_json(out_path)
        if not output.get("summary"):
            failures += 1
            results.append(
                {
                    "module": module,
                    "source": source,
                    "target": target,
                    "error": "scanner output has no summary",
                    "stderr": completed.stderr.strip()[-2000:],
                }
            )
            continue
        total.update(output.get("summary", {}))
        results.append(
            {
                "module": module,
                "source": source,
                "target": target,
                "out": out_path,
                "summary": output.get("summary", {}),
            }
        )

    merged = {
        "transitions": results,
        "total": dict(sorted(total.items())),
        "failures": failures,
    }
    merged_path = os.path.join(out_dir, "batch_summary.json")
    with open(merged_path, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=1)
    print(json.dumps(merged["total"], indent=2), file=sys.stderr)
    print(f"written {merged_path}", file=sys.stderr)
    if failures:
        print(f"{failures} transition(s) failed", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
