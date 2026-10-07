"""Exact envelope construction. Python standard library only.

The exhaustive routines are bounded research oracles, not scalable controllers.
All scientific arithmetic is rational. Delayed copies are independent points
of the same box; no inter-time reachability restriction is silently imposed.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import combinations, product
from math import comb
from typing import Iterable

Q = Fraction

def rational(value: object) -> Q:
    if isinstance(value, bool) or not isinstance(value, (str, int, Fraction)):
        raise ValueError("rational data must be an integer or rational string")
    try:
        return Q(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("invalid rational") from exc

def parse_model(data: dict) -> tuple[int, tuple]:
    d = data.get("dimension")
    if type(d) is not int or d < 0:
        raise ValueError("dimension must be a nonnegative integer")
    rows = []
    if not isinstance(data.get("rows"), list):
        raise ValueError("rows must be a list")
    for row in data["rows"]:
        a, w = rational(row["a"]), rational(row["weight"])
        b = tuple(map(rational, row["b"]))
        if len(b) != d or w <= 0 or a <= sum(map(abs, b), Q(0)):
            raise ValueError("row violates dimension, positive weight, or price margin")
        rows.append((a, b, w))
    return d, tuple(rows)

def vertices(d: int) -> Iterable[tuple[int, ...]]:
    if type(d) is not int or not 0 <= d <= 16:
        raise ValueError("exhaustive oracle is restricted to dimension at most 16")
    return product((-1, 1), repeat=d)

def value(row: tuple, z: tuple) -> Q:
    a, b, w = row
    if len(b) != len(z):
        raise ValueError("assignment length mismatch")
    return w / (a + sum((c * v for c, v in zip(b, z)), Q(0)))

def coherent(rows: tuple | list, d: int) -> tuple[Q, tuple]:
    best, witness = Q(-1), ()
    for z in vertices(d):
        score = sum((value(row, z) for row in rows), Q(0))
        if score > best:
            best, witness = score, z
    return best, witness

def rectangular(rows: tuple | list) -> Q:
    return sum((w / (a - sum(map(abs, b), Q(0))) for a, b, w in rows), Q(0))

def h(k: int, theta: Q) -> Q:
    theta = rational(theta)
    if type(k) is not int or k < 1 or not 0 <= theta < 1:
        raise ValueError("require k >= 1 and 0 <= theta < 1")
    return sum((Q(comb(k, j), 2**k) / (1 + theta * Q(2*j-k, k))
                for j in range(k+1)), Q(0))

def sharp_constant(k: int, theta: Q) -> Q:
    return 1 / ((1-theta) * h(k, theta))

def partitions(n: int, r: int) -> Iterable[tuple[tuple[int, ...], ...]]:
    """Unlabelled partitions into at most r nonempty cohorts."""
    if type(n) is not int or type(r) is not int or not 0 <= n <= 9 or r < 1:
        raise ValueError("partition oracle requires 0 <= n <= 9 and r >= 1")
    groups: list[list[int]] = []
    def visit(i: int):
        if i == n:
            yield tuple(tuple(g) for g in groups)
            return
        for j in range(len(groups)):
            groups[j].append(i)
            yield from visit(i+1)
            groups[j].pop()
        if len(groups) < r:
            groups.append([i])
            yield from visit(i+1)
            groups.pop()
    yield from visit(0)

def stamped(rows: tuple | list, d: int, r: int) -> tuple[Q, tuple]:
    cache: dict[tuple, Q] = {}
    best, best_partition = Q(-1), ()
    for partition in partitions(len(rows), r):
        total = Q(0)
        for group in partition:
            if group not in cache:
                cache[group] = coherent([rows[i] for i in group], d)[0]
            total += cache[group]
        if total > best:
            best, best_partition = total, partition
    return best, best_partition

def conflict_edges(rows: tuple | list) -> set[tuple[int, int]]:
    return {(i, j) for i in range(len(rows)) for j in range(i+1, len(rows))
            if any(x*y < 0 for x, y in zip(rows[i][1], rows[j][1]))}

def make_certificate(data: dict, bags: list[list[int]], parents: list[int],
                     owners: list[int]) -> dict:
    """Construct exact separator messages; a separate checker validates them.

    Input layout uses root bag 0 and parent indices smaller than child indices.
    The constructor is not the trusted validator of decomposition semantics.
    """
    d, rows = parse_model(data)
    if not bags or len(bags) != len(parents) or parents[0] != -1:
        raise ValueError("invalid rooted bag list")
    if len(owners) != len(rows) or any(len(b) > 16 for b in bags):
        raise ValueError("owner length or oracle width limit")
    bs = [tuple(sorted(b)) for b in bags]
    children = [[] for _ in bs]
    for t in range(1, len(bs)):
        if not 0 <= parents[t] < t:
            raise ValueError("constructor expects parent-before-child order")
        children[parents[t]].append(t)
    tables: list[dict[str, Q]] = [{} for _ in bs]
    for t in reversed(range(len(bs))):
        separator = () if t == 0 else tuple(sorted(set(bs[t]) & set(bs[parents[t]])))
        local = [(a, tuple((i, coefficient) for i, coefficient in enumerate(b) if coefficient), w)
                 for row, own in zip(rows, owners) if own == t
                 for a, b, w in (row,)]
        child_separators = [(child, tuple(sorted(set(bs[child]) & set(bs[t]))))
                            for child in children[t]]
        for sign in vertices(len(bs[t])):
            assign = dict(zip(bs[t], sign))
            total = Q(0)
            for a, support, w in local:
                total += w/(a + sum((coefficient*assign[i] for i, coefficient in support), Q(0)))
            for child, sep_child in child_separators:
                key_child = ",".join(str(assign[i]) for i in sep_child)
                total += tables[child][key_child]
            key = ",".join(str(assign[i]) for i in separator)
            tables[t][key] = max(tables[t].get(key, Q(-1)), total)
    return {"bags": [list(b) for b in bs], "parents": parents, "owners": owners,
            "messages": [{key: str(v) for key, v in table.items()} for table in tables],
            "upper_bound": str(tables[0][""])}

def h_antipodal(k: int, theta: Q) -> Q:
    """Balanced-row average for a uniformly random antipodal stamp pair."""
    theta = rational(theta)
    if type(k) is not int or k < 1 or not 0 <= theta < 1:
        raise ValueError("require k >= 1 and 0 <= theta < 1")
    return sum((Q(comb(k, j), 2**k) / (1-theta*Q(abs(2*j-k), k))
                for j in range(k+1)), Q(0))

def sharp_two_stamp_constant(k: int, theta: Q) -> Q:
    return 1 / ((1-theta)*h_antipodal(k,theta))

def support_two_constant(stamps: int, theta: Q) -> Q:
    """Closed sharp constants proved for support at most two, stamps 2--5."""
    theta = rational(theta)
    beta = {2: Q(1,2), 3: Q(2,3), 4: Q(5,6), 5: Q(7,8)}
    if type(stamps) is not int or stamps not in beta or not 0 <= theta < 1:
        raise ValueError("closed formula requires stamps in {2,3,4,5}, 0 <= theta < 1")
    return 1/(1-(1-beta[stamps])*theta)

def palette_average(k: int, stamps: int, theta: Q, distribution: dict[tuple, Q]) -> Q:
    """Evaluate G(pi; theta) exactly for a supplied finite column distribution.

    This does not optimize the polynomial and is not a general sharp-constant
    solver. Resource guards describe this evaluator, not the mathematical class.
    Columns use signs +/-1 and canonical first entry +1.
    """
    theta = rational(theta)
    if (type(k) is not int or not 1 <= k <= 5 or type(stamps) is not int
            or not 1 <= stamps <= 5 or not 0 <= theta < 1):
        raise ValueError("evaluator requires 1 <= k, stamps <= 5 and 0 <= theta < 1")
    if not distribution or sum(distribution.values(), Q(0)) != 1:
        raise ValueError("distribution must have total mass one")
    for column, probability in distribution.items():
        if (len(column) != stamps or column[0] != 1 or
                any(type(x) is not int or x not in (-1,1) for x in column) or
                not isinstance(probability, (int,Q)) or isinstance(probability,bool) or probability < 0):
            raise ValueError("invalid column or exact probability")
    if len(distribution)**k * 2**k > 200000:
        raise ValueError("finite evaluator term budget exceeded")
    answer=Q(0)
    for columns in product(tuple(distribution), repeat=k):
        probability=Q(1)
        for column in columns:
            probability*=distribution[column]
        if not probability:
            continue
        value=Q(0)
        for signs in product((-1,1), repeat=k):
            dot=min(sum(signs[i]*columns[i][j] for i in range(k)) for j in range(stamps))
            value+=1/(1+theta*Q(dot,k))
        answer+=probability*value/2**k
    return answer

def qi_clique_size(stamps: int) -> int:
    """Size of the Kleitman--Spencer qualitative-independence clique used here."""
    if type(stamps) is not int or stamps < 4:
        raise ValueError("require at least four stamps")
    return comb(stamps - 1, stamps // 2 - 1)


def qi_clique_columns(stamps: int) -> tuple[tuple[int, ...], ...]:
    """Explicit canonical columns with every distinct pair realizing all four signs.

    Coordinate zero is fixed to +1.  Among the remaining coordinates, the
    negative set has cardinality ceil(stamps/2).  Equal cardinality makes two
    distinct sets incomparable, while their size makes them intersect.
    """
    if type(stamps) is not int or stamps < 4:
        raise ValueError("require at least four stamps")
    negative_size = (stamps + 1) // 2
    columns = []
    for negative in combinations(range(1, stamps), negative_size):
        column = [1] * stamps
        for index in negative:
            column[index] = -1
        columns.append(tuple(column))
    answer = tuple(columns)
    if len(answer) != qi_clique_size(stamps):
        raise AssertionError("qualitative-independence construction size mismatch")
    return answer


def pair_pattern_count(first: tuple[int, ...], second: tuple[int, ...]) -> int:
    """Number of distinct ordered sign pairs realized by two stamp columns."""
    if not first or len(first) != len(second):
        raise ValueError("columns must be nonempty and have equal length")
    if any(value not in (-1, 1) for value in first + second):
        raise ValueError("columns must contain only signs")
    return len(set(zip(first, second)))


def support_two_sandwich(stamps: int, theta: Q) -> tuple[Q, Q]:
    """Exact rational all-stamp lower/upper bounds for the sharp support-two factor.

    The lower endpoint is the collision noncollapse bound specialized to k=2.
    The upper endpoint is witnessed by the explicit qualitative-independence
    clique distribution.  The function does not claim equality for stamps > 5.
    """
    theta = rational(theta)
    if type(stamps) is not int or stamps < 4 or not 0 <= theta < 1:
        raise ValueError("require stamps >= 4 and 0 <= theta < 1")
    clique = qi_clique_size(stamps)
    lower = 1 / (1 - theta / Q(2**stamps))
    upper = 1 / (1 - theta / Q(2 * clique))
    return lower, upper
