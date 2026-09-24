"""Exact three-stamp correlation and command-transition experiment.

The experiment directly exercises the paper's complete support-two family.  It
is a deterministic rational falsification test, not a packet-network or learned
predictor simulation.
"""
from fractions import Fraction as Q
from itertools import combinations, product

DIMENSION = 3
THETA = Q(1, 2)
CAPACITY = Q(21)
ROW_SIGNS = tuple((pair, signs)
                  for pair in combinations(range(DIMENSION), 2)
                  for signs in product((-1, 1), repeat=2))
# Columns are the three nonconstant canonical classes for r=3.  Transposing
# gives three global stamp corners.
COLUMNS = ((1, 1, -1), (1, -1, 1), (1, -1, -1))
BASE_STAMPS = tuple(tuple(COLUMNS[i][j] for i in range(DIMENSION))
                    for j in range(3))
GRAY_CYCLE = (0, 1, 3, 2, 6, 7, 5, 4)


def _rate(pair, signs, stamp):
    i, j = pair
    denominator = Q(1) + Q(1, 4) * (signs[0] * stamp[i] + signs[1] * stamp[j])
    assert denominator > 0
    return 1 / denominator


def _flips(mask):
    return tuple(-1 if mask >> i & 1 else 1 for i in range(DIMENSION))


def _stamps(mask):
    flips = _flips(mask)
    return tuple(tuple(flips[i] * stamp[i] for i in range(DIMENSION))
                 for stamp in BASE_STAMPS)


def _target(mask):
    stamps = _stamps(mask)
    rates = tuple(max(_rate(pair, signs, stamp) for stamp in stamps)
                  for pair, signs in ROW_SIGNS)
    assert rates.count(Q(2)) == 9 and rates.count(Q(1)) == 3
    assert sum(rates, Q(0)) == CAPACITY
    return rates


def _load(state):
    return sum(state, Q(0))


def _direct_three_stamp_oracle():
    corners = tuple(product((-1, 1), repeat=DIMENSION))
    best = Q(-1)
    witnesses = []
    evaluations = 0
    for stamps in product(corners, repeat=3):
        value = sum((max(_rate(pair, signs, stamp) for stamp in stamps)
                     for pair, signs in ROW_SIGNS), Q(0))
        evaluations += 1
        if value > best:
            best, witnesses = value, [stamps]
        elif value == best and len(witnesses) < 4:
            witnesses.append(stamps)
    return best, witnesses, evaluations


def run_correlated_pipeline():
    """Return exact evidence for the correlation-aware safety interface."""
    assert len(ROW_SIGNS) == 12
    assert all(len(stamp) == DIMENSION for stamp in BASE_STAMPS)
    oracle, witnesses, oracle_evaluations = _direct_three_stamp_oracle()
    rectangular = Q(24)
    assert oracle == CAPACITY < rectangular

    targets = {mask: _target(mask) for mask in GRAY_CYCLE}
    records = []
    checked_states = 0
    maximum_intermediate = Q(0)
    for position, old_mask in enumerate(GRAY_CYCLE):
        new_mask = GRAY_CYCLE[(position + 1) % len(GRAY_CYCLE)]
        old, target = targets[old_mask], targets[new_mask]
        middle = tuple(min(a, b) for a, b in zip(old, target))
        reduction_max = Q(0)
        increase_max = Q(0)
        # Exhaust every subset of already applied coordinates in each phase.
        for subset in range(1 << len(old)):
            reduction = tuple(middle[s] if subset >> s & 1 else old[s]
                              for s in range(len(old)))
            increase = tuple(target[s] if subset >> s & 1 else middle[s]
                             for s in range(len(old)))
            reduction_load, increase_load = _load(reduction), _load(increase)
            assert reduction_load <= CAPACITY and increase_load <= CAPACITY
            reduction_max = max(reduction_max, reduction_load)
            increase_max = max(increase_max, increase_load)
            maximum_intermediate = max(maximum_intermediate,
                                       reduction_load, increase_load)
            checked_states += 2
        records.append({
            "old_mask": old_mask,
            "new_mask": new_mask,
            "changed_sources": sum(a != b for a, b in zip(old, target)),
            "middle_load": str(_load(middle)),
            "maximum_reduction_load": str(reduction_max),
            "maximum_increase_load": str(increase_max),
        })

    original = targets[0]
    complemented = _target(7)
    asynchronous_mix = tuple(max(a, b) for a, b in zip(original, complemented))
    assert all(value == 2 for value in asynchronous_mix)
    assert _load(asynchronous_mix) == rectangular > CAPACITY

    rowwise_gamma = CAPACITY / rectangular
    assert rowwise_gamma == Q(7, 8)
    rowwise_target = tuple(rowwise_gamma * value for value in original)
    assert _load(rowwise_target) == Q(147, 8)

    return {
        "dimension": DIMENSION,
        "theta": str(THETA),
        "source_count": len(ROW_SIGNS),
        "stamp_count": 3,
        "base_stamps": [list(stamp) for stamp in BASE_STAMPS],
        "coherent_three_stamp_envelope": str(oracle),
        "rowwise_envelope": str(rectangular),
        "capacity": str(CAPACITY),
        "correlation_aware_gamma": "1",
        "rowwise_gamma": str(rowwise_gamma),
        "rowwise_filtered_load": str(_load(rowwise_target)),
        "proportional_utility_loss": "12*log(8/7)",
        "oracle_stamp_tuples": oracle_evaluations,
        "oracle_witnesses_retained": [[list(z) for z in stamps]
                                      for stamps in witnesses],
        "epochs": len(GRAY_CYCLE),
        "transitions": records,
        "transition_count": len(records),
        "intermediate_states": checked_states,
        "maximum_intermediate_load": str(maximum_intermediate),
        "unbarriered_mix_load": str(_load(asynchronous_mix)),
        "unbarriered_mix_overload": str(_load(asynchronous_mix) - CAPACITY),
    }
