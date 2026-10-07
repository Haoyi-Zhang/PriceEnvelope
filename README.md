# Correlated safety envelopes

This standalone research repository contains exact finite oracles, an independently implemented separator-certificate checker, and a small commanded-rate control experiment for positive reciprocal-affine price families. The complete 41-page mathematical manuscript is included as `proofs/theory.pdf`; no sibling `paper/` directory is needed.

## Reproduce

Use Python 3.10 or later on a POSIX system providing the standard-library `resource` module. No package installation, network, solver, trained predictor, GPU, or external service is required. From the repository root run:

```sh
python reproduce.py --output reproduced --check-against results
python check_certificate.py results/certificate_model.json results/certificate.json --capacity 9/2
python export_figures.py --output reproduced-figures
python tests/pilot.py --output reproduced-pilot.json
```

The first command regenerates all deterministic evidence and compares the parsed exact result with the delivered reference. Resource measurements are deliberately excluded from exact equality. The main runner is one process with a 1 GiB address-space limit and 120 CPU-second limit. The remaining commands check the worked certificate, export the two plot tables, and rerun the intake pilot.

Expected certificate output is `CERTIFIED upper bound: 9/2`. Running the same checker with capacity `449/100` must exit nonzero with `REJECTED: capacity not certified`; this deliberate rejection is a negative test.

An aggregate delivered-check verifier is also available:

```sh
python -B verify_release.py
```

It binds `results/certificate_model.json` and `results/certificate.json` by their exact names, runs an order-reversal fixture for the former wildcard hazard, reruns the main reproduction, checks the positive and strict-negative certificate queries, exercises the malformed-input and tampered-reference tests, and exactly checks the two certificate-slack examples stated after Proposition 6.8. The supplied packet does **not** contain the previously referenced `independent_random_exact_cases.py` implementation or a frozen result for 128 such cases. Accordingly, `verify_release.py` neither executes nor reports those 128 cases and prints the omission explicitly. This missing supplemental asset does not change the documented main reproduction command above, which is independently run and compared with `results`.

The suite includes 33 complete-pair palette extrema, eight direct stamp-tuple checks, 39 explicit five-stamp constructions plus an exact line-graph spectral certificate, 15 all-stamp support-two sandwich checks, 1,099 Max-Cut identities, 285 coloring/stamp comparisons, 225 fixed-stamp reduction checks, 285 weighted-deletion cases, 22 variational grids, 72 constructor/checker/brute-force certificate oracle cases, 20 rejected certificate mutations, and 7,404 safe transition orders. The two-link pipeline has 12 runs, 768 certified targets, and 4,608 intermediate states. A separate correlation-aware experiment enumerates 512 stamp triples and 65,536 two-phase intermediate states across eight epochs. See `inputs/case-specification.md` for all counts and selection rules.

For an in-process check of the release manifest, the worked capacity boundary, and 32 rejections of the 16 owned malformed-input classes, run `python -B tests/check_integrity.py --output /tmp/p105-integrity-inputs` with a new output directory. Fixtures and rejection reasons are retained; this does not rerun the mathematical suite or constitute black-box CLI testing.

The `Scientific finite checks` workflow runs on pushes to `main` or manual dispatch from this standalone repository root, not a sibling project directory. On Ubuntu 24.04 it preserves the manifest, exact-result comparison, worked-certificate acceptance/rejection, owned-input rejection, and changed-reference rejection gates. The whole command sequence has a 420-second wall limit, inherited 1 GiB address-space and 300 CPU-second limits, and a ten-minute job limit; the reproduction core retains its own 120 CPU-second limit. Raw logs, results, and owned fixtures are uploaded even on failure. Preparing this workflow does not establish that it has run. Successful finite checks do not establish the unrestricted theorems or deployment safety.

## Model and scientific scope

The current constructor prepares each owned row's ordered nonzero coefficients
and each child separator once per bag, outside sign enumeration. Every corner,
exact rational sum, message key, and checker inequality is retained; this is
fixed-structure preparation, not a new algorithm for unrestricted safety. The
four portable regression methods compare every conditional subtree table with
an independent dense definition oracle on the retained 72-case generator and
six boundary/decomposition cases, plus checker controls and a width-16 constant
case. From this repository root run:

```sh
python -B -m unittest discover -s tests -p test_prepared_messages.py -v
```

The existing scientific workflow includes this step without replacing any old
gate. Frozen `results/`, resource observations and the delivered proof remain
unchanged evidence from before this preparation change. Local finite agreement
does not certify the full reproduction or establish a measured speedup. The
release manifest binds current packaged bytes; updating its changed source/test
entries is not a refresh of frozen experiment evidence.

A row is `weight / (a + b dot z)` over one latent box `[-1,1]^d`, with `weight > 0` and `a > sum(abs(b))`. The coherent envelope uses one common `z`; the r-stamp envelope permits at most r latent versions of this same affine family and an adverse row-to-version assignment; the rectangular envelope maximizes every row independently. This is an information contract, not a claim that every stamp tuple is reachable by a feedback law.

The paper proves sharp reserve-factor characterizations, explicit one/two-stamp and support-two three/four/five-stamp constants, an all-stamp support-two sandwich, a dimension-free approximate-recovery versus logarithmic exact-saturation separation, finite complete-family formulas, a graph saturation threshold with a fixed-stamp complexity dichotomy and weighted deficits, a fixed-radius hardness reduction, and sound local upper certificates. It also proves a safe command transition and a separate sufficient delayed contraction result. Standard packing, column-distribution, coloring, decomposition, robust-optimization, and asynchronous-convergence precedents are attributed and calibrated in `literature_calibration.csv`; their use alone is not claimed as novel.

The artifact separates two control checks. The complete support-two experiment has `M_3=21<R=24`, compares correlation-aware and rowwise attenuation, exhausts every two-phase subset state, and retains an unsafe unbarriered-mixing negative control. The two-link delayed pipeline uses a sign-compatible interval where the three envelopes coincide and isolates the contraction/safety-transfer interface. Neither is a packet-network measurement, trained-predictor study, or algorithm for discovering the optimum.

## Files and trust boundaries

`src/envelope.py` contains bounded exhaustive oracles and a certificate constructor. `src/checker.py` imports neither the constructor nor its evaluator/parser. The caller supplies the intended model. The checker validates positive prices, tree structure, coverage, running intersection, unique ownership, complete separator tables, local majorization, and the optional capacity comparison. Code separation is not independent human review.

The checker allows at most 256 bags of size at most 16. The corner oracle permits dimension at most 16; the partition oracle permits at most 9 rows; the generic palette evaluator has a separate term bound. Exceeding a software limit is inconclusive and does not narrow the general theorem. The command-state class is a benign mathematical simulator, not a production transport or parser-security library.

`tests/validate.py`, `tests/variational.py`, `tests/correlated_pipeline.py`, and `tests/control_pipeline.py` define the finite mathematical cases. `tests/reference_audit.py` independently verifies the delivered 56-row reference manifest against the external-resource and literature-calibration ledgers; its summary is retained in `results/reference_audit.json` and inside `results/exact_results.json`. `results/exact_results.json`, `results/correlated_pipeline.json`, and `results/control_pipeline.json` retain realized rational evidence. `proofs/model.md` fixes interpretation. `claim_evidence_ledger.csv` maps material claims to proofs and checks. `external_resources.csv` records stable scholarly sources for all 56 cited works, while `literature_calibration.csv` records the 23-paper closest-work core and supplementary source-level boundaries for every cited work. No scholarly PDF or publisher macro is redistributed.
