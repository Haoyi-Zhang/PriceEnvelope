"""Portable finite constructor checks; no private stages or service dependencies."""
from copy import deepcopy
from fractions import Fraction as Q
from itertools import product
import random
import unittest
from src.envelope import make_certificate
from src.checker import check, InvalidCertificate


def cases():
    """Replay the retained 72-case generator without producer helpers."""
    rng = random.Random(20260916)
    for case in range(72):
        d = 1 + case % 6
        bags = [list(range(d))] if d <= 3 else [list(range(t, t + 3)) for t in range(d - 2)]
        rows, owners = [], []
        for j in range(1 + (case * 5) % 8):
            owner = rng.randrange(len(bags))
            bag = bags[owner]
            support = rng.sample(bag, rng.randrange(len(bag) + 1))
            if j == 0 and not support:
                support = [bag[case % len(bag)]]
            b = [Q(0)] * d
            for i in support:
                b[i] = rng.choice((-1, 1)) * Q(rng.randint(1, 3), 12)
            rows.append(dict(a='2', b=list(map(str, b)), weight=str(rng.randint(1, 5))))
            owners.append(owner)
        yield dict(dimension=d, rows=rows), bags, [-1] + list(range(len(bags) - 1)), owners
    yield dict(dimension=0, rows=[]), [[]], [-1], []
    yield dict(dimension=0, rows=[dict(a='2', b=[], weight='3')]), [[]], [-1], [0]
    yield dict(dimension=3, rows=[]), [[2, 0], [1]], [-1, 0], []
    rows = [dict(a='3', b=['1/4', '-1/3', '0', '0'], weight='2'),
            dict(a='2', b=['0', '0', '-1/2', '0'], weight='1'),
            dict(a='4', b=['0', '0', '0', '1/3'], weight='3'),
            dict(a='2', b=['0'] * 4, weight='1')]
    model = dict(dimension=4, rows=rows)
    yield model, [[1, 0], [2, 0], [3]], [-1, 0, 0], [0, 1, 2, 0]
    yield model, [[0, 1], [1, 0], [2, 3]], [-1, 0, 1], [1, 2, 2, 0]
    yield dict(dimension=8, rows=[dict(a='2', b=['1/5'] + ['0'] * 7, weight='3')]), \
        [[i, i + 1] for i in range(7)], [-1] + list(range(6)), [0]


def definition_tables(model, bags, parents, owners):
    """Full dense-row conditional subtree maxima, not a message recurrence.

    These cases use at most eight coordinates in a subtree.
    """
    rows = [(Q(row['a']), tuple(map(Q, row['b'])), Q(row['weight'])) for row in model['rows']]
    answer = []
    for t, bag in enumerate(bags):
        subtree = {t}
        for child in range(t + 1, len(bags)):
            if parents[child] in subtree:
                subtree.add(child)
        coordinates = sorted(set().union(*(set(bags[j]) for j in subtree)))
        separator = [] if t == 0 else sorted(set(bag) & set(bags[parents[t]]))
        values = {}
        for signs in product((-1, 1), repeat=len(coordinates)):
            assign = dict(zip(coordinates, signs))
            score = Q(0)
            for (a, b, weight), owner in zip(rows, owners):
                if owner in subtree:
                    score += weight / (a + sum((c * assign[i] for i, c in enumerate(b) if c), Q(0)))
            key = ','.join(str(assign[i]) for i in separator)
            values[key] = max(values.get(key, Q(-1)), score)
        answer.append({key: str(value) for key, value in values.items()})
    return answer


class PreparedMessagesTests(unittest.TestCase):
    def test_all_conditional_tables_and_input_preservation(self):
        for args in cases():
            saved = deepcopy(args)
            cert = make_certificate(*args)
            with self.subTest(model=args[0], bags=args[1]):
                self.assertEqual(cert['messages'], definition_tables(*args))
                self.assertEqual(cert['upper_bound'], cert['messages'][0][''])
                self.assertEqual(args, saved)

    def test_independent_checker_capacity_and_conservative_slack(self):
        for args in cases():
            cert = make_certificate(*args)
            upper = Q(definition_tables(*args)[0][''])
            self.assertEqual(check(args[0], cert, upper), upper)
            with self.assertRaises(InvalidCertificate):
                check(args[0], cert, upper - Q(1, 100))
            loose = deepcopy(cert)
            loose['messages'][0][''] = loose['upper_bound'] = str(upper + 1)
            self.assertEqual(check(args[0], loose), upper + 1)

    def test_checker_still_rejects_invalid_decompositions(self):
        model, bags, parents, owners = list(cases())[75]
        cert = make_certificate(model, bags, parents, owners)
        for field, replacement in [('owners', [2, 1, 2, 0]),
                                   ('owners', [3, 1, 2, 0]),
                                   ('bags', [[0, 1], [0, 2], [1, 3]]),
                                   ('bags', [[0, 1], [0, 2], []])]:
            changed = deepcopy(cert)
            changed[field] = replacement
            with self.assertRaises(InvalidCertificate):
                check(model, changed)

    def test_maximum_local_width_constant_row(self):
        model = dict(dimension=16, rows=[dict(a='2', b=['0'] * 16, weight='3')])
        cert = make_certificate(model, [list(reversed(range(16)))], [-1], [0])
        self.assertEqual(cert['messages'], [{'': '3/2'}])
        self.assertEqual(check(model, cert), Q(3, 2))


if __name__ == '__main__':
    unittest.main()
