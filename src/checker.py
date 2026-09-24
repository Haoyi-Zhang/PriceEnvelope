"""Independent local-inequality certificate checker.

Does not import the envelope solver, its parser, its objective evaluator, or its
message constructor. This separation is not a claim of independent human review.
The caller supplies the immutable model explicitly, so a certificate is never
accepted merely because it contains its own preferred instance.
"""
from fractions import Fraction
from itertools import product

class InvalidCertificate(ValueError):
    pass

def _q(x):
    if isinstance(x, bool) or not isinstance(x, (int, str, Fraction)):
        raise InvalidCertificate("non-rational encoding")
    try:
        return Fraction(x)
    except (ValueError, ZeroDivisionError) as exc:
        raise InvalidCertificate("invalid rational encoding") from exc

def check(model: dict, certificate: dict, capacity=None) -> Fraction:
    try:
        return _check(model, certificate, capacity)
    except InvalidCertificate:
        raise
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise InvalidCertificate("malformed structure") from exc

def _check(model, cert, capacity):
    d = model["dimension"]
    if type(d) is not int or d < 0:
        raise InvalidCertificate("invalid dimension")
    rows = []
    if not isinstance(model["rows"], list):
        raise InvalidCertificate("invalid rows")
    for obj in model["rows"]:
        a, w = _q(obj["a"]), _q(obj["weight"])
        coeff = tuple(_q(t) for t in obj["b"])
        if len(coeff) != d or w <= 0 or a <= sum(abs(t) for t in coeff):
            raise InvalidCertificate("invalid domain")
        rows.append((a, coeff, w))
    rawbags, parent = cert["bags"], cert["parents"]
    if not isinstance(rawbags, list) or not rawbags or len(rawbags) > 256:
        raise InvalidCertificate("invalid bag count or checker resource bound")
    count = len(rawbags)
    if not isinstance(parent, list) or len(parent) != count or type(parent[0]) is not int or parent[0] != -1:
        raise InvalidCertificate("invalid rooted tree")
    bags = []
    for raw in rawbags:
        if (not isinstance(raw, list) or any(type(i) is not int or not 0 <= i < d for i in raw)
                or len(set(raw)) != len(raw) or len(raw) > 16):
            raise InvalidCertificate("invalid bag or width resource bound")
        bags.append(set(raw))
    children = [[] for _ in bags]
    for t in range(1, count):
        p = parent[t]
        if type(p) is not int or not 0 <= p < count or p == t:
            raise InvalidCertificate("invalid parent")
        children[p].append(t)
    visited, stack = set(), [0]
    while stack:
        u = stack.pop()
        if u in visited:
            raise InvalidCertificate("tree cycle")
        visited.add(u)
        stack.extend(children[u])
    if len(visited) != count:
        raise InvalidCertificate("disconnected tree")
    for i in range(d):
        containing = {t for t, bag in enumerate(bags) if i in bag}
        if not containing:
            raise InvalidCertificate("uncovered variable")
        reached, stack = set(), [next(iter(containing))]
        while stack:
            t = stack.pop()
            if t in reached:
                continue
            reached.add(t)
            neighbors = children[t] + ([parent[t]] if t else [])
            stack.extend(v for v in neighbors if v in containing and v not in reached)
        if reached != containing:
            raise InvalidCertificate("running intersection fails")
    owners = cert["owners"]
    if not isinstance(owners, list) or len(owners) != len(rows):
        raise InvalidCertificate("each factor needs one owner")
    local = [[] for _ in bags]
    for i, t in enumerate(owners):
        if type(t) is not int or not 0 <= t < count:
            raise InvalidCertificate("invalid factor owner")
        support = {j for j, b in enumerate(rows[i][1]) if b}
        if not support <= bags[t]:
            raise InvalidCertificate("factor scope absent from owner bag")
        local[t].append(rows[i])
    rawmessages = cert["messages"]
    if not isinstance(rawmessages, list) or len(rawmessages) != count:
        raise InvalidCertificate("message count mismatch")
    separators, messages = [], []
    for t in range(count):
        separator = sorted(bags[t] & bags[parent[t]]) if t else []
        separators.append(separator)
        expected = {",".join(map(str, s)) for s in product((-1, 1), repeat=len(separator))}
        raw = rawmessages[t]
        if not isinstance(raw, dict) or set(raw) != expected:
            raise InvalidCertificate("missing or extra separator assignment")
        messages.append({key: _q(value) for key, value in raw.items()})
    for t, bag in enumerate(bags):
        coordinates = sorted(bag)
        for signs in product((-1, 1), repeat=len(bag)):
            assignment = dict(zip(coordinates, signs))
            rhs = Fraction(0)
            for a, coeff, weight in local[t]:
                denominator = a
                for i, b in enumerate(coeff):
                    if b:
                        denominator += b * assignment[i]
                rhs += weight / denominator
            for u in children[t]:
                key = ",".join(str(assignment[i]) for i in separators[u])
                rhs += messages[u][key]
            key = ",".join(str(assignment[i]) for i in separators[t])
            if messages[t][key] < rhs:
                raise InvalidCertificate("local majorization inequality fails")
    upper = _q(cert["upper_bound"])
    if upper != messages[0][""]:
        raise InvalidCertificate("root upper bound mismatch")
    if capacity is not None and upper > _q(capacity):
        raise InvalidCertificate("capacity not certified")
    return upper
