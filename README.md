# Generated-System QA Pattern

A small, dependency-free checker for generated worlds, workflows, maps, and
other graph-shaped systems.

It verifies that generated data matches its current input, edges are valid,
required services exist and are reachable, named goals can be reached within a
step budget, and one representative journey is actually legal.

All fixtures are synthetic. The checker does not call a model, execute a
generator, start a server, or use the network.

## Why It Exists

Unit tests can pass while generated content is stale, disconnected, missing a
required service, or impossible to traverse through the route shown to a user.
Structural readiness needs its own explicit proof.

This pattern keeps two evidence classes separate:

- **Structural QA:** deterministic checks for freshness, integrity, coverage,
  reachability, and a representative journey.
- **Experience QA:** a human decides whether the journey is understandable,
  useful, interesting, or fun.

## Run

Requires Python 3.10 or newer.

```sh
python3 -B generated_system_qa.py examples/good.json
python3 -B generated_system_qa.py --self-test
python3 -B -m unittest discover -s tests -v
```

Expected result for the good case:

```text
PASS generated_system_qa good.json
```

The self-test also proves that an unreachable goal, stale generation digest,
missing service, and illegal representative journey fail with named codes.

## What It Checks

- The generated artifact records the SHA-256 digest of the current blueprint.
- Every node ID is unique and every edge references declared nodes.
- Required services exist on nodes reachable from the entry.
- Goals are reachable within the configured step budget.
- Optional all-node reachability holds when requested.
- The representative journey follows real edges, reaches a goal, stays within
  the step budget, and visits each required service.

## Fixture Shape

The case file points to a blueprint and generated world, then declares the
entry, goals, required services, route budget, reachability posture, and one
representative journey. The generated world contains nodes, directed edges,
and the blueprint digest from which it claims to have been built.

The example uses a tiny fictional harbor with a dock, workshop, market, and
archive. It contains no game, customer, or production data.

## What A Pass Does Not Prove

A pass does not prove that the generator itself is deterministic, that every
possible journey works, that a live UI serves current assets, or that the
system is enjoyable. It does not replace domain-specific simulation,
performance checks, accessibility review, or a real human journey.

## Public Data Notice

Use synthetic fixtures. Do not add private maps, customer workflows, unreleased
content, production exports, credentials, or raw telemetry to examples or
issues.
