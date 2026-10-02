# Generated-System QA Pattern

Check whether a generated map or workflow still matches its input and can be
followed from start to finish along one chosen route. This small Python checker
works with graphs: named places or steps (nodes), joined by directed links
(edges).

Try the fictional harbor example below. Its route should reach a goal, stay
within a step limit, and visit the required services. Deliberately broken
examples show what happens when a service is missing or a route cannot work.

All fixtures are synthetic. The checker does not call a model, execute a
generator, start a server, or use the network. It needs no extra dependencies.

## Why It Exists

Generated content can become stale when its input changes. It can also contain
places that cannot be reached, omit a required service, or show a route that
uses a link that does not exist. Use these checks alongside your other tests
to catch those specific problems.

Keep two questions separate:

- **Does the data meet the declared rules?** The checker compares the saved
  input and generated data, then checks links, services, goals and one route.
- **Is the experience good?** A person still needs to try the journey and judge
  whether it is understandable, useful, interesting or fun.

## Run

From this repository’s folder, run these commands with Python 3.10 or newer:

```sh
python3 -B generated_system_qa.py examples/good.json
python3 -B generated_system_qa.py --self-test
python3 -B -m unittest discover -s tests -v
```

Expected result for the good case:

```text
PASS generated_system_qa good.json
```

The first pass means the saved harbor data meets the rules in `good.json`.
The self-test checks that an unreachable goal, an outdated input fingerprint,
a missing service and an illegal route each fail with a named code. The last
command runs the test suite.

<!-- toolkit-trust-card:placement -->

<!-- toolkit-trust-card:start -->
> **Public contract:** Experimental pattern · about 10 min · Python 3 · no model · no network
>
> **Operation:** Read-only check; examples may use temporary files
>
> **A pass establishes:** The supplied artifact matches its blueprint and satisfies the declared structural and journey requirements.
>
> **It does not establish:** Structural readiness does not prove live UI freshness, domain quality, accessibility, or enjoyment.
>
> **First check:** `python3 -B generated_system_qa.py --self-test`
<!-- toolkit-trust-card:end -->

## What It Checks

- The generated file records the SHA-256 digest (a fingerprint of the bytes)
  of the current blueprint, the input that describes what to generate.
- Every node ID is unique and every edge references declared nodes.
- Required services exist on nodes reachable from the entry.
- Goals are reachable within the configured step budget.
- Every node can be reached from the entry, if the case requires that.
- The representative journey follows real edges, reaches a goal, stays within
  the step budget, and visits each required service.

## Fixture Shape

The case file names the blueprint and generated world to compare. It also
specifies where to start, which goals and services to reach, the maximum number
of steps, whether every node must be reachable, and one route to check. The
world file contains the nodes, directed edges and fingerprint of the blueprint
from which it claims to have been built.

The example uses a tiny fictional harbor with a dock, workshop, market and
archive. Compare `examples/good.json` with the bad case files to see which
requirement each one breaks. It contains no game, customer or production data.

## What A Pass Does Not Prove

A pass does not prove that the generator itself is deterministic, that every
possible journey works, that a live UI serves current assets, or that the
system is enjoyable. It does not replace domain-specific simulation,
performance checks, accessibility review, or a real human journey.

## Public Data Notice

Use synthetic fixtures. Do not add private maps, customer workflows, unreleased
content, production exports, credentials, or raw telemetry to examples or
issues.
