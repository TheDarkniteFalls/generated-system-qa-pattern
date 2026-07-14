#!/usr/bin/env python3
"""Check structural readiness and one representative journey in generated data."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_JSON_BYTES = 1_000_000
CASE_FIELDS = {
    "schema_version",
    "system_id",
    "blueprint_path",
    "world_path",
    "entry_node",
    "goal_nodes",
    "required_services",
    "max_goal_steps",
    "require_all_nodes_reachable",
    "representative_journey",
}
WORLD_FIELDS = {"schema_version", "generated_from_sha256", "nodes", "edges"}


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError(f"{path.name} exceeds one megabyte")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} root must be an object")
    return value


def _safe_path(case_dir: Path, supplied: object) -> Path | None:
    if not isinstance(supplied, str) or not supplied:
        return None
    relative = Path(supplied)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    resolved = (case_dir / relative).resolve()
    try:
        resolved.relative_to(case_dir.resolve())
    except ValueError:
        return None
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finding(findings: list[Finding], code: str, message: str) -> None:
    findings.append(Finding(code, message))


def _distances(entry: str, adjacency: dict[str, set[str]]) -> dict[str, int]:
    distances = {entry: 0}
    queue = deque([entry])
    while queue:
        current = queue.popleft()
        for target in sorted(adjacency[current]):
            if target not in distances:
                distances[target] = distances[current] + 1
                queue.append(target)
    return distances


def validate_case(case: dict[str, Any], world: dict[str, Any], case_dir: Path) -> list[Finding]:
    findings: list[Finding] = []

    unknown_case = sorted(set(case) - CASE_FIELDS)
    missing_case = sorted(CASE_FIELDS - set(case))
    if unknown_case:
        _finding(findings, "UNKNOWN_CASE_FIELD", f"unknown case fields: {', '.join(unknown_case)}")
    if missing_case:
        _finding(findings, "MISSING_CASE_FIELD", f"missing case fields: {', '.join(missing_case)}")
        return findings
    if case.get("schema_version") != 1:
        _finding(findings, "CASE_SCHEMA", "case schema_version must be 1")

    unknown_world = sorted(set(world) - WORLD_FIELDS)
    missing_world = sorted(WORLD_FIELDS - set(world))
    if unknown_world:
        _finding(findings, "UNKNOWN_WORLD_FIELD", f"unknown world fields: {', '.join(unknown_world)}")
    if missing_world:
        _finding(findings, "MISSING_WORLD_FIELD", f"missing world fields: {', '.join(missing_world)}")
        return findings
    if world.get("schema_version") != 1:
        _finding(findings, "WORLD_SCHEMA", "world schema_version must be 1")

    blueprint_path = _safe_path(case_dir, case.get("blueprint_path"))
    if blueprint_path is None:
        _finding(findings, "BLUEPRINT_PATH", "blueprint_path is unsafe")
    elif not blueprint_path.is_file():
        _finding(findings, "BLUEPRINT_MISSING", "blueprint file is missing")
    else:
        current_digest = _sha256(blueprint_path)
        if world.get("generated_from_sha256") != current_digest:
            _finding(findings, "GENERATED_DRIFT", "generated world does not match the current blueprint digest")

    raw_nodes = world.get("nodes")
    nodes: dict[str, set[str]] = {}
    if not isinstance(raw_nodes, list) or not raw_nodes:
        _finding(findings, "NODES", "nodes must be a non-empty list")
    else:
        for index, node in enumerate(raw_nodes):
            if not isinstance(node, dict):
                _finding(findings, "NODE_SHAPE", f"node {index} must be an object")
                continue
            node_id = node.get("id")
            services = node.get("services")
            if not isinstance(node_id, str) or not node_id:
                _finding(findings, "NODE_ID", f"node {index} has an invalid id")
                continue
            if node_id in nodes:
                _finding(findings, "DUPLICATE_NODE", f"duplicate node id: {node_id}")
                continue
            if not isinstance(services, list) or not all(isinstance(item, str) and item for item in services):
                _finding(findings, "NODE_SERVICES", f"{node_id} services must be a string list")
                services = []
            if len(services) != len(set(services)):
                _finding(findings, "DUPLICATE_SERVICE", f"{node_id} declares duplicate services")
            nodes[node_id] = set(services)

    adjacency = {node_id: set() for node_id in nodes}
    edge_pairs: set[tuple[str, str]] = set()
    raw_edges = world.get("edges")
    if not isinstance(raw_edges, list):
        _finding(findings, "EDGES", "edges must be a list")
    else:
        for index, edge in enumerate(raw_edges):
            if not isinstance(edge, dict):
                _finding(findings, "EDGE_SHAPE", f"edge {index} must be an object")
                continue
            source = edge.get("from")
            target = edge.get("to")
            if source not in nodes or target not in nodes:
                _finding(findings, "EDGE_TARGET", f"edge {index} references an unknown node")
                continue
            pair = (source, target)
            if pair in edge_pairs:
                _finding(findings, "DUPLICATE_EDGE", f"duplicate edge: {source} -> {target}")
                continue
            edge_pairs.add(pair)
            adjacency[source].add(target)

    entry = case.get("entry_node")
    if not isinstance(entry, str) or entry not in nodes:
        _finding(findings, "ENTRY_NODE", "entry_node must name a declared node")
        distances: dict[str, int] = {}
    else:
        distances = _distances(entry, adjacency)

    goals = case.get("goal_nodes")
    if not isinstance(goals, list) or not goals or not all(isinstance(item, str) for item in goals):
        _finding(findings, "GOAL_NODES", "goal_nodes must be a non-empty string list")
        goals = []
    max_steps = case.get("max_goal_steps")
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps < 1:
        _finding(findings, "MAX_GOAL_STEPS", "max_goal_steps must be a positive integer")
        max_steps = 0
    for goal in goals:
        if goal not in nodes:
            _finding(findings, "UNKNOWN_GOAL", f"goal is not declared: {goal}")
        elif goal not in distances:
            _finding(findings, "GOAL_UNREACHABLE", f"goal is unreachable from entry: {goal}")
        elif distances[goal] > max_steps:
            _finding(findings, "GOAL_TOO_DISTANT", f"goal exceeds max_goal_steps: {goal}")

    if case.get("require_all_nodes_reachable") is not True and case.get("require_all_nodes_reachable") is not False:
        _finding(findings, "REACHABILITY_FLAG", "require_all_nodes_reachable must be boolean")
    elif case.get("require_all_nodes_reachable") is True:
        for node_id in sorted(set(nodes) - set(distances)):
            _finding(findings, "UNREACHABLE_NODE", f"node is unreachable from entry: {node_id}")

    required_services = case.get("required_services")
    if not isinstance(required_services, list) or not all(isinstance(item, str) and item for item in required_services):
        _finding(findings, "REQUIRED_SERVICES", "required_services must be a string list")
        required_services = []
    if len(required_services) != len(set(required_services)):
        _finding(findings, "DUPLICATE_REQUIRED_SERVICE", "required_services must be unique")
    for service in required_services:
        providers = {node_id for node_id, node_services in nodes.items() if service in node_services}
        if not providers:
            _finding(findings, "SERVICE_MISSING", f"required service is absent: {service}")
        elif not providers.intersection(distances):
            _finding(findings, "SERVICE_UNREACHABLE", f"required service is unreachable: {service}")

    journey = case.get("representative_journey")
    if not isinstance(journey, list) or not journey or not all(isinstance(item, str) for item in journey):
        _finding(findings, "JOURNEY", "representative_journey must be a non-empty string list")
        journey = []
    if journey:
        if journey[0] != entry:
            _finding(findings, "JOURNEY_START", "representative journey must start at entry_node")
        if not goals or journey[-1] not in goals:
            _finding(findings, "JOURNEY_GOAL", "representative journey must end at a goal node")
        if len(journey) - 1 > max_steps:
            _finding(findings, "JOURNEY_TOO_LONG", "representative journey exceeds max_goal_steps")
        for node_id in journey:
            if node_id not in nodes:
                _finding(findings, "JOURNEY_NODE", f"journey references unknown node: {node_id}")
        for source, target in zip(journey, journey[1:]):
            if source in adjacency and target not in adjacency[source]:
                _finding(findings, "JOURNEY_EDGE", f"journey step is not an edge: {source} -> {target}")
        journey_services = set().union(*(nodes.get(node_id, set()) for node_id in journey))
        for service in required_services:
            if service not in journey_services:
                _finding(findings, "JOURNEY_SERVICE", f"journey does not visit required service: {service}")

    return findings


def check_path(case_path: Path) -> list[Finding]:
    try:
        case = _load_json(case_path)
        world_path = _safe_path(case_path.parent, case.get("world_path"))
        if world_path is None:
            return [Finding("WORLD_PATH", "world_path is unsafe")]
        if not world_path.is_file():
            return [Finding("WORLD_MISSING", "generated world file is missing")]
        world = _load_json(world_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [Finding("CASE_LOAD", str(exc))]
    return validate_case(case, world, case_path.parent)


SELF_TEST_CASES = {
    "good.json": (True, None),
    "bad_unreachable.json": (False, "GOAL_UNREACHABLE"),
    "bad_drift.json": (False, "GENERATED_DRIFT"),
    "bad_missing_service.json": (False, "SERVICE_MISSING"),
    "bad_journey.json": (False, "JOURNEY_EDGE"),
}


def run_self_test(root: Path) -> int:
    failures = 0
    for name, (should_pass, expected_code) in SELF_TEST_CASES.items():
        findings = check_path(root / "examples" / name)
        codes = {finding.code for finding in findings}
        passed = not findings
        correct = passed == should_pass and (expected_code is None or expected_code in codes)
        print(f"{'PASS' if correct else 'FAIL'} fixture {name}")
        failures += not correct
    if failures:
        print(f"FAIL self_test {failures} fixture expectations failed")
        return 1
    print("PASS self_test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", nargs="?", type=Path, help="path to a generated-system QA case")
    parser.add_argument("--self-test", action="store_true", help="run bundled pass/fail fixtures")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    if args.self_test:
        return run_self_test(root)
    if args.case is None:
        parser.error("provide a case path or --self-test")

    findings = check_path(args.case.resolve())
    if findings:
        for finding in findings:
            print(f"FAIL {finding.code} {finding.message}")
        return 1
    print(f"PASS generated_system_qa {args.case.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
