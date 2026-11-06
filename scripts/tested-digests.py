#!/usr/bin/env python3
"""The record of what a candidate run tested, and main's check of it.

ci.yml runs candidate mode in the develop -> main promotion pull request: it
builds every image that differs from main as build-containers.yml publishes it,
pushes it untagged by digest, tests that digest on every platform and tags it
candidate-<tree12>. Its candidate-tag job then writes tested-digests.json and
uploads it as the run's `tested-digests` artifact. A push to main checks that
the promotion run which tested its tree wrote one, and 2d publishes the digests
it names without building them again.

The record is written even when the promotion changed no image, with an empty
images map, so main can prove its tree was tested either way:

    {"base": <main's commit the run was based on>, "head": <the develop commit
     built and tested>, "images": {<name>: <index digest>}, "run_id": <run>,
     "tree": <the head's tree>}

  write --digests DIR --images JSON --base true|false --tree T --head H
        --base-sha B --run-id N --output FILE
      Builds the record from the candidate builds' digest files in DIR, one
      {"name", "digest"} JSON file per image. Their names must be exactly the
      images the changes job resolved, and base when it was built: a record
      that left one out would let main publish an image nobody tested.

  find-run --repository R --sha S
      For a push to main: the pull request merged as S, which must come from
      develop, and its newest successful ci.yml pull_request run, which must
      have a tested-digests artifact. Prints run_id=, pr= and head= for
      $GITHUB_OUTPUT. Reads the GitHub API through `gh api` (GH_TOKEN, with
      actions: read and pull-requests: read).

  verify --record FILE --tree T --run-id N
      Fails unless the record is well formed, came from run N and names tree T,
      the tree of the commit main is at.

Every failure prints ::error:: with what to do, and exits 1. Usage errors exit 2.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

WORKFLOW = "ci.yml"
ARTIFACT = "tested-digests"
SOURCE_BRANCH = "develop"
TARGET_BRANCH = "main"
BASE = "base"
SHA_RE = re.compile(r"[0-9a-f]{40}")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
RECORD_KEYS = {"base", "head", "images", "run_id", "tree"}


class RecordError(Exception):
    """A record, or the run behind it, that main cannot rely on."""


def _sha(value: str, what: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise RecordError(f"{what} is {json.dumps(value)}, not a 40-character SHA-1")
    return value


def _run_id(value: str | int) -> int:
    if isinstance(value, bool) or not re.fullmatch(r"[1-9][0-9]*", str(value)):
        raise RecordError(f"run_id is {json.dumps(value)}, not a run id")
    return int(value)


def _images(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise RecordError(f"images is {json.dumps(value)}, not an object")
    for name, digest in value.items():
        if not NAME_RE.fullmatch(name):
            raise RecordError(f"{json.dumps(name)} is not an image name")
        if not isinstance(digest, str) or not DIGEST_RE.fullmatch(digest):
            raise RecordError(
                f"{name}'s digest {json.dumps(digest)} is not sha256:<64 hex>"
            )
    return dict(value)


def read_digests(directory: Path) -> dict[str, str]:
    """The {name: digest} of every candidate build's digest file in directory."""
    digests: dict[str, str] = {}
    files = sorted(directory.glob("*.json")) if directory.is_dir() else []
    for path in files:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise RecordError(f"{path.name} cannot be read: {exc}") from exc
        if not isinstance(entry, dict) or set(entry) != {"name", "digest"}:
            raise RecordError(
                f"{path.name} is {json.dumps(entry)}, not {{name, digest}}"
            )
        name = entry["name"]
        if not isinstance(name, str) or path.name != f"{name}.json":
            raise RecordError(f"{path.name} names the image {json.dumps(name)}")
        digests.update(_images({name: entry["digest"]}))
    return digests


def build_record(
    digests: dict[str, str],
    images: Any,
    base_built: bool,
    tree: str,
    head: str,
    base_sha: str,
    run_id: str,
) -> dict[str, Any]:
    """The record, once the digests are exactly the images the run built."""
    if not isinstance(images, list) or not all(isinstance(i, str) for i in images):
        raise RecordError(
            f"expected a JSON list of image names, got {json.dumps(images)}"
        )
    expected = set(images) | ({BASE} if base_built else set())
    if set(digests) != expected:
        missing = ", ".join(sorted(expected - set(digests))) or "none"
        extra = ", ".join(sorted(set(digests) - expected)) or "none"
        raise RecordError(
            f"the run built {', '.join(sorted(expected)) or 'no image'}, but the"
            f" digests on record do not match (missing: {missing}; not built: {extra})"
        )
    return {
        "base": _sha(base_sha, "base"),
        "head": _sha(head, "head"),
        "images": dict(sorted(digests.items())),
        "run_id": _run_id(run_id),
        "tree": _sha(tree, "tree"),
    }


def check_record(record: Any, tree: str, run_id: str) -> dict[str, str]:
    """The record's images, once it is well formed and names this tree and run."""
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        keys = sorted(record) if isinstance(record, dict) else record
        raise RecordError(
            f"the record has {json.dumps(keys)}, not {sorted(RECORD_KEYS)}"
        )
    _sha(record["base"], "base")
    _sha(record["head"], "head")
    images = _images(record["images"])
    if _run_id(record["run_id"]) != _run_id(run_id):
        raise RecordError(f"the record is run {record['run_id']}'s, not run {run_id}'s")
    if _sha(record["tree"], "tree") != _sha(tree, "this commit's tree"):
        raise RecordError(
            f"run {run_id} tested tree {record['tree']} (develop {record['head']}), but"
            f" main has tree {tree}: main took a tree no candidate run tested. Merge"
            f" main into {SOURCE_BRANCH} and let the promotion pull request's candidate"
            " run test the result before anything is published from it"
        )
    return images


def _gh_api(path: str, kind: type) -> Any:
    proc = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RecordError(f"gh api {path} failed: {proc.stderr.strip()}")
    try:
        answer = json.loads(proc.stdout)
    except ValueError as exc:
        raise RecordError(f"gh api {path} returned no JSON: {exc}") from exc
    if not isinstance(answer, kind):
        raise RecordError(
            f"gh api {path} returned {type(answer).__name__}, not {kind.__name__}"
        )
    return answer


def find_run(repository: str, sha: str) -> dict[str, str]:
    """The promotion pull request merged as sha, and the run that tested it."""
    pulls = _gh_api(f"repos/{repository}/commits/{sha}/pulls", list)
    merged = [
        pull
        for pull in pulls
        if isinstance(pull, dict)
        and pull.get("merged_at")
        and pull.get("merge_commit_sha") == sha
        and pull.get("base", {}).get("ref") == TARGET_BRANCH
    ]
    if not merged:
        raise RecordError(
            f"no pull request merged into {TARGET_BRANCH} has {sha} as its merge"
            f" commit: {TARGET_BRANCH} moved without the promotion pull request, whose"
            " candidate run tests what main takes. Revert it and promote"
            f" {SOURCE_BRANCH} instead"
        )
    pull = merged[0]
    number = pull["number"]
    head = pull.get("head", {})
    if (
        head.get("ref") != SOURCE_BRANCH
        or head.get("repo", {}).get("full_name") != repository
    ):
        raise RecordError(
            f"pull request #{number} merged {head.get('label', head.get('ref'))} into"
            f" {TARGET_BRANCH}, which takes only {repository}'s {SOURCE_BRANCH}: no"
            " candidate run tested it. Revert it and promote"
            f" {SOURCE_BRANCH} instead"
        )
    head_sha = _sha(head.get("sha", ""), f"pull request #{number}'s head")
    runs = _gh_api(
        f"repos/{repository}/actions/workflows/{WORKFLOW}/runs"
        f"?event=pull_request&head_sha={head_sha}&status=success&per_page=100",
        dict,
    )
    passed = sorted(
        (
            run
            for run in runs.get("workflow_runs", [])
            if isinstance(run, dict)
            and run.get("event") == "pull_request"
            and run.get("conclusion") == "success"
            and run.get("head_sha") == head_sha
            and run.get("head_branch") == SOURCE_BRANCH
            # A fork's pull request can have develop's exact head and a
            # branch named develop; its run has no record.
            and isinstance(run.get("head_repository"), dict)
            and run["head_repository"].get("full_name") == repository
        ),
        key=lambda run: (run.get("run_started_at") or "", run["id"]),
    )
    if not passed:
        raise RecordError(
            f"pull request #{number} has no successful {WORKFLOW} run for its head"
            f" {head_sha}: it merged before its candidate run passed. Re-run that"
            " run, then this job"
        )
    run_id = passed[-1]["id"]
    artifacts = _gh_api(
        f"repos/{repository}/actions/runs/{run_id}/artifacts?name={ARTIFACT}", dict
    )
    if not any(
        isinstance(artifact, dict)
        and artifact.get("name") == ARTIFACT
        and not artifact.get("expired")
        for artifact in artifacts.get("artifacts", [])
    ):
        raise RecordError(
            f"run {run_id} of pull request #{number} has no unexpired {ARTIFACT}"
            " artifact: it ran without candidate mode, or the record expired. Re-run"
            " its candidate jobs, then this job"
        )
    return {"run_id": str(run_id), "pr": str(number), "head": head_sha}


def _fail(exc: Exception) -> int:
    print(f"::error title=Candidate record::{exc}", file=sys.stderr)
    return 1


def _write(args: argparse.Namespace) -> int:
    if args.base not in ("true", "false"):
        return _fail(
            RecordError(f"--base is {json.dumps(args.base)}, not true or false")
        )
    try:
        record = build_record(
            read_digests(Path(args.digests)),
            json.loads(args.images),
            args.base == "true",
            args.tree,
            args.head,
            args.base_sha,
            args.run_id,
        )
    except (RecordError, ValueError) as exc:
        return _fail(exc)
    Path(args.output).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Tree {record['tree']} (develop {record['head']}), run {record['run_id']}:")
    for name, digest in record["images"].items() or [("no image built", "")]:
        print(f"  {name} {digest}".rstrip())
    return 0


def _find_run(args: argparse.Namespace) -> int:
    try:
        found = find_run(args.repository, _sha(args.sha, "--sha"))
    except RecordError as exc:
        return _fail(exc)
    for key, value in found.items():
        print(f"{key}={value}")
    return 0


def _verify(args: argparse.Namespace) -> int:
    try:
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
        images = check_record(record, args.tree, args.run_id)
    except (OSError, UnicodeDecodeError, ValueError, RecordError) as exc:
        return _fail(exc)
    print(f"Run {args.run_id} tested tree {args.tree}, develop {record['head']}:")
    for name, digest in images.items() or [("no image changed", "")]:
        print(f"  {name} {digest}".rstrip())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    write = commands.add_parser("write", help="Write a candidate run's record.")
    write.add_argument("--digests", required=True, help="Digest files' directory.")
    write.add_argument("--images", required=True, help="JSON list, base not in it.")
    write.add_argument("--base", required=True, help="true when base was built.")
    write.add_argument("--tree", required=True, help="The head's tree.")
    write.add_argument("--head", required=True, help="The develop commit built.")
    write.add_argument("--base-sha", required=True, help="main's commit.")
    write.add_argument("--run-id", required=True, help="This run's id.")
    write.add_argument("--output", required=True, help="Where to write it.")
    find = commands.add_parser("find-run", help="The run that tested a main push.")
    find.add_argument("--repository", required=True, help="owner/name.")
    find.add_argument("--sha", required=True, help="The commit pushed to main.")
    verify = commands.add_parser("verify", help="Check a record against a tree.")
    verify.add_argument("--record", required=True, help="tested-digests.json.")
    verify.add_argument("--tree", required=True, help="The tree main is at.")
    verify.add_argument("--run-id", required=True, help="The run it came from.")
    args = parser.parse_args(argv)

    if args.command == "write":
        return _write(args)
    if args.command == "find-run":
        return _find_run(args)
    return _verify(args)


if __name__ == "__main__":
    sys.exit(main())
