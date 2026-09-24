"""Deterministic finite checks and deliberately incorrect negative controls."""
from fractions import Fraction as Q
from itertools import product, combinations, permutations
from math import ceil, log2
from copy import deepcopy
import random
from src.envelope import (vertices, value, coherent, rectangular, sharp_constant,
                          h, stamped, conflict_edges, parse_model, make_certificate,
                          h_antipodal, sharp_two_stamp_constant, support_two_constant, palette_average)
from src.checker import check, InvalidCertificate
from src.transition import Transition

SEED = 20260911

def as_model(rows, d):
    return {"dimension": d, "rows": [
        {"a": str(a), "b": list(map(str, b)), "weight": str(w)} for a, b, w in rows]}

def allsign_rows(k, theta):
    return [(Q(1), tuple(theta*Q(s,k) for s in z), Q(1)) for z in vertices(k)]

def graph_rows(n, edges):
    rows = []
    for u, v in edges:
        b = [Q(0)]*n
        b[u], b[v] = Q(1,2), -Q(1,2)
        rows.extend([(Q(4), tuple(b), Q(30)), (Q(4), tuple(-x for x in b), Q(30))])
    return rows

def coloring_rows(n, edges):
    delta = max([sum(v in e for e in edges) for v in range(n)] + [1])
    rows = []
    for v in range(n):
        b = [Q(1,2*delta) if v == u else -Q(1,2*delta) if v == w else Q(0)
             for u, w in edges]
        rows.append((Q(1), tuple(b), Q(1)))
    return rows

def colorable(n, edges, r):
    # Independent brute coloring, no envelope imports or cohort enumeration.
    return any(all(colors[u] != colors[v] for u,v in edges)
               for colors in product(range(r), repeat=n))

def fixed_r_saturation_reduction_tests():
    """Check the join reduction used for every fixed r >= 3."""
    records=[]
    for n in range(1,5):
        possible=list(combinations(range(n),2))
        for mask in range(2**len(possible)):
            edges=[e for i,e in enumerate(possible) if mask>>i&1]
            base_three=colorable(n,edges,3)
            for r in (3,4,5):
                clique_size=r-3
                new_vertices=list(range(n,n+clique_size))
                joined=list(edges)
                joined.extend(combinations(new_vertices,2))
                joined.extend((u,v) for u in range(n) for v in new_vertices)
                joined=sorted(set(joined))
                total=n+clique_size
                assert colorable(total,joined,r)==base_three
                rows=coloring_rows(total,joined)
                assert conflict_edges(rows)==set(joined)
                assert all(sum(abs(x) for x in b)<=Q(1,2) for a,b,w in rows)
                assert all(a==w==1 for a,b,w in rows)
                records.append({"n":n,"edge_mask":mask,"stamps":r,
                                "joined_vertices":total,"joined_edges":joined,
                                "base_three_colorable":base_three})
    return records

def direct_copy_oracle(rows, d, r):
    best = Q(-1)
    for copies in product(tuple(vertices(d)), repeat=r):
        score = Q(0)
        for a, b, w in rows:
            best_row = max(w/(a+sum((b[i]*z[i] for i in range(d)),Q(0))) for z in copies)
            score += best_row
        best = max(best, score)
    return best

def sharp_tests():
    rows_out = []
    for k in range(1, 7):
        for theta in (Q(1,4), Q(1,2), Q(3,4)):
            rows = allsign_rows(k, theta)
            m, _ = coherent(rows, k)
            rec = rectangular(rows)
            exact = sharp_constant(k, theta)
            assert rec/m == exact
            assert exact <= min(Q(2**k), 1/(1-theta))
            assert 1+theta*theta/k <= h(k,theta) <= 1+theta*theta/(k*(1-theta*theta))
            rows_out.append({"k": k, "theta": str(theta), "M1": str(m),
                             "R": str(rec), "ratio": str(exact)})
    rng = random.Random(SEED)
    cases = []
    for index in range(240):
        d, n = 1+index%6, 1+(index//6)%6
        k = 1+index%d
        theta = (Q(1,4),Q(1,2),Q(3,4))[index%3]
        rows = []
        for _ in range(n):
            support = rng.sample(range(d), rng.randint(0,k))
            raw = [rng.randint(1,5) for _ in support]
            total = sum(raw)
            radius = theta * Q(rng.randint(0,4),4)
            b = [Q(0)]*d
            for coord, mag in zip(support,raw):
                b[coord] = rng.choice((-1,1))*radius*Q(mag,total)
            rows.append((Q(1),tuple(b),Q(rng.randint(1,5))))
        m,_ = coherent(rows,d)
        rec = rectangular(rows)
        assert m <= rec <= sharp_constant(k,theta)*m
        cases.append({"case": index, "k": k, "theta": str(theta), "model": as_model(rows,d),
                      "M1": str(m), "R": str(rec)})
    return rows_out,cases

def maxcut_tests():
    results = []
    for n in range(1,6):
        possible = list(combinations(range(n),2))
        for mask in range(2**len(possible)):
            edges = [e for i,e in enumerate(possible) if mask>>i&1]
            rows = graph_rows(n,edges)
            # Pure combinatorial cut count is independent of reciprocal evaluation.
            cut = max(sum(z[u] != z[v] for u,v in edges) for z in vertices(n))
            m,witness = coherent(rows,n)
            assert m == 15*len(edges)+cut
            # Verify the strict half-integer decision threshold as well as the identity.
            thresholds=[]
            for target in range(len(edges)+2):
                capacity=15*len(edges)+Q(target)-Q(1,2)
                unsafe=m>capacity
                assert unsafe==(cut>=target)
                thresholds.append({"target":target,"capacity":str(capacity),"unsafe":unsafe})
            results.append({"n":n,"edge_mask":mask,"edges":edges,
                            "M1":str(m),"max_cut":cut,"witness":witness,"thresholds":thresholds})
    return results

def stamp_tests():
    results=[]
    for n in range(1,5):
        possible=list(combinations(range(n),2))
        for mask in range(2**len(possible)):
            edges=[e for i,e in enumerate(possible) if mask>>i&1]
            rows=coloring_rows(n,edges)
            assert conflict_edges(rows)==set(edges)
            rec=rectangular(rows)
            previous=Q(0)
            for r in range(1,n+1):
                m,partition=stamped(rows,len(edges),r)
                assert (m==rec)==colorable(n,edges,r)
                assert previous<=m<=rec
                previous=m
                results.append({"n":n,"edge_mask":mask,"stamps":r,
                                "Mr":str(m),"R":str(rec),"cohorts":partition})
    direct_cases=[]
    for d in range(1,4):
        rows=allsign_rows(d,Q(1,2))[:min(4,2**d)]
        for r in range(1,4):
            cohort,_=stamped(rows,d,r)
            direct=direct_copy_oracle(rows,d,r)
            assert cohort==direct
            direct_cases.append({"d":d,"stamps":r,"value":str(cohort)})
    return results,direct_cases

def covering_tests():
    records=[]
    for d in range(2,17):
        length=(d-1).bit_length()
        matrix=[[0]*d,[1]*d]
        for bit in range(length):
            row=[(j>>bit)&1 for j in range(d)]
            matrix.extend([row,[1-x for x in row]])
        for u,v in combinations(range(d),2):
            assert {(row[u],row[v]) for row in matrix}=={(0,0),(0,1),(1,0),(1,1)}
        records.append({"dimension":d,"constructed_stamps":len(matrix),"matrix":matrix})
    # Exact small stamp minima, independent bit-mask set-cover enumeration.
    exact=[]
    for d in range(2,5):
        pairs=list(combinations(range(d),2))
        masks=[]
        for row in product((0,1),repeat=d):
            mask=0
            for j,(u,v) in enumerate(pairs):
                mask |= 1 << (4*j+2*row[u]+row[v])
            masks.append(mask)
        full=(1<<(4*len(pairs)))-1
        optimum=None
        for r in range(1,7):
            for subset in combinations(range(1,len(masks)),r-1):
                mask=masks[0] # Coordinate complementation permits fixing one row.
                for i in subset: mask|=masks[i]
                if mask==full:
                    optimum=r;break
            if optimum is not None: break
        assert optimum is not None
        exact.append({"dimension":d,"minimum_stamps":optimum})
    return records,exact

def certificate_tests():
    rows=[(Q(2),(Q(1,4),Q(-1,4),Q(0),Q(0)),Q(1)),
          (Q(2),(Q(0),Q(1,4),Q(1,4),Q(0)),Q(2)),
          (Q(2),(Q(0),Q(0),Q(-1,4),Q(1,4)),Q(3)),
          (Q(1),(Q(0),)*4,Q(1))]
    model=as_model(rows,4)
    cert=make_certificate(model,[[0,1],[1,2],[2,3]],[-1,0,1],[0,1,2,0])
    upper=check(model,cert)
    assert upper==coherent(rows,4)[0]
    bad=[]
    def add(name,fn):
        obj=deepcopy(cert);fn(obj);bad.append((name,obj))
    add("root_understatement",lambda x:x["messages"][0].update({"":"0"}))
    add("reported_bound_only",lambda x:x.update(upper_bound="0"))
    add("child_understatement",lambda x:x["messages"][2].update({"-1":"0"}))
    add("missing_assignment",lambda x:x["messages"][1].pop("-1"))
    add("extra_assignment",lambda x:x["messages"][1].update({"0":"0"}))
    add("missing_owner",lambda x:x["owners"].pop())
    add("scope_wrong_owner",lambda x:x["owners"].__setitem__(0,2))
    add("owner_out_of_range",lambda x:x["owners"].__setitem__(0,3))
    add("owner_boolean",lambda x:x["owners"].__setitem__(0,True))
    add("tree_cycle",lambda x:x["parents"].__setitem__(1,2))
    add("bad_root",lambda x:x["parents"].__setitem__(0,0))
    add("float_root",lambda x:x["parents"].__setitem__(0,-1.0))
    add("duplicate_variable",lambda x:x["bags"][0].append(0))
    add("out_of_range_variable",lambda x:x["bags"][0].append(4))
    add("running_intersection",lambda x:x["bags"][2].append(0))
    add("missing_variable",lambda x:x["bags"][2].remove(3))
    add("float_encoding",lambda x:x["messages"][0].update({"":1.0}))
    add("zero_denominator",lambda x:x["messages"][0].update({"":"1/0"}))
    rejected=[]
    for name,obj in bad:
        try: check(model,obj)
        except InvalidCertificate: rejected.append(name)
        else: raise AssertionError("accepted corrupted certificate: "+name)
    changed=deepcopy(model);changed["rows"][0]["weight"]="100"
    try: check(changed,cert)
    except InvalidCertificate: rejected.append("changed_input_weight")
    else: raise AssertionError("certificate not bound to input")
    try: check(model,cert,upper-Q(1,100))
    except InvalidCertificate: rejected.append("insufficient_capacity")
    else: raise AssertionError("insufficient capacity accepted")
    # Valid conservative certificates must not be rejected solely for looseness.
    loose=deepcopy(cert)
    loose["messages"][0][""]=str(upper+1);loose["upper_bound"]=str(upper+1)
    assert check(model,loose)==upper+1
    boundary=[]
    for obj in ({"dimension":0,"rows":[]},
                {"dimension":0,"rows":[{"a":"2","b":[],"weight":"3"}]},
                {"dimension":1,"rows":[]}):
        bags=[list(range(obj["dimension"]))]
        c=make_certificate(obj,bags,[-1],[0]*len(obj["rows"]))
        check(obj,c)
        boundary.append({"model":obj,"certificate":c})
    return model,cert,rejected,boundary

def certificate_oracle_tests():
    """Cross-check exact certificates against an independent brute-force oracle.

    The instances are generated so every factor scope belongs to a bag in a
    width-two path decomposition.  The oracle below parses neither through the
    envelope module nor through the checker and evaluates every cube vertex
    directly from the serialized model.
    """
    rng=random.Random(SEED+5)
    records=[]
    for case in range(72):
        d=1+case%6
        if d<=3:
            bags=[list(range(d))]
        else:
            bags=[list(range(t,t+3)) for t in range(d-2)]
        parents=[-1]+list(range(len(bags)-1))
        rows=[];owners=[]
        row_count=1+(case*5)%8
        for row_index in range(row_count):
            owner=rng.randrange(len(bags))
            bag=bags[owner]
            support=rng.sample(bag,rng.randrange(len(bag)+1))
            # Ensure that every nontrivial test batch contains a scoped factor.
            if row_index==0 and not support:
                support=[bag[case%len(bag)]]
            coeff=[Q(0)]*d
            for coordinate in support:
                coeff[coordinate]=rng.choice((-1,1))*Q(rng.randint(1,3),12)
            # At most three coefficients of magnitude 1/4, so a=2 leaves a
            # strict positive margin under every sign assignment.
            rows.append((Q(2),tuple(coeff),Q(rng.randint(1,5))))
            owners.append(owner)
        model=as_model(rows,d)
        certificate=make_certificate(model,bags,parents,owners)
        certified=check(model,certificate)

        brute=Q(-1)
        for signs in product((-1,1),repeat=d):
            total=Q(0)
            for obj in model["rows"]:
                a=Q(obj["a"]);weight=Q(obj["weight"])
                denominator=a+sum((Q(value)*sign for value,sign in zip(obj["b"],signs)),Q(0))
                total+=weight/denominator
            brute=max(brute,total)
        assert certified==brute
        assert check(model,certificate,brute)==brute
        try:
            check(model,certificate,brute-Q(1,100))
        except InvalidCertificate:
            pass
        else:
            raise AssertionError("certificate accepted a capacity below its exact bound")
        records.append({"case":case,"dimension":d,"rows":row_count,
                        "bags":len(bags),"exact_upper":str(brute)})
    return records


def transition_tests():
    rng=random.Random(SEED+1)
    total=0;records=[]
    for n in range(1,5):
        cap=Q(n)
        feasible=[tuple(map(Q,v)) for v in product((0,1,2),repeat=n) if sum(v)<=n]
        for index in range(12):
            old,target=rng.choice(feasible),rng.choice(feasible)
            orders=list(permutations(range(n)))
            for down in orders:
                for up in orders:
                    machine=Transition(old,target)
                    assert not machine.apply(1,"increase",0)
                    assert not machine.apply(0,"decrease",0)
                    for i in down:
                        assert machine.apply(1,"decrease",i)
                        assert sum(machine.rates)<=cap
                    for i in up:
                        assert machine.apply(1,"increase",i)
                        assert not machine.apply(1,"decrease",i)
                        assert sum(machine.rates)<=cap
                    assert tuple(machine.rates)==target
                    total+=1
            records.append({"n":n,"case":index,"old":list(map(str,old)),
                            "target":list(map(str,target)),"capacity":str(cap)})
    old=(Q(2),Q(2,3));target=old[::-1]
    assert sum(old)==sum(target)==Q(8,3)
    assert old[0]+target[1]==4>3
    return total,records

def contraction_tests():
    # Finite sanity checks of the generic theorem, not log-dual performance data.
    q=Q(3,8);epsilon=Q(1,64);radius=epsilon/(1-q)
    reports=[]
    for delay in range(4):
        B=2;T=delay+B
        history=[(Q(1,2),Q(-1,2))]
        for k in range(120):
            state=list(history[-1]);i=k%2
            j=1-i
            a=history[max(0,k-delay)][i]
            b=history[max(0,k-(delay if k%3 else 0))][j]
            error=epsilon*(-1 if k%5 else 1)
            state[i]=Q(1,4)*a+Q(1,8)*b+error
            history.append(tuple(state))
            bound=radius+q**((k+1)//T)*(Q(1,2)-radius)
            assert max(map(abs,state))<=bound
        reports.append({"delay":delay,"update_gap":B,"updates":120,
                        "q":str(q),"epsilon":str(epsilon),"radius":str(radius),
                        "final_error":str(max(map(abs,history[-1])))})
    eta,e,p=Q(1,2),Q(1,8),Q(4,3)
    assert p-eta*(1-1/p)+e==p and 1/p==Q(3,4)
    return reports


def two_stamp_tests():
    records=[]
    for k in range(1,5):
        for theta in (Q(1,4),Q(1,2),Q(3,4)):
            rows=allsign_rows(k,theta)
            actual=direct_copy_oracle(rows,k,2)
            rec=rectangular(rows)
            assert rec/actual==sharp_two_stamp_constant(k,theta)
            # Independent enumeration includes pairs that are not antipodal.
            records.append({"k":k,"theta":str(theta),"M2":str(actual),
                            "R":str(rec),"ratio":str(rec/actual)})
    general=[]
    rng=random.Random(SEED+2)
    for case in range(48):
        d=1+case%4; k=1+case%d;theta=Q(1+(case%3),4)
        rows=[]
        for j in range(1+case%6):
            support=rng.sample(range(d),rng.randint(0,k))
            raw=[rng.randint(1,4) for _ in support]; total=sum(raw)
            b=[Q(0)]*d
            for i,v in zip(support,raw):
                b[i]=rng.choice((-1,1))*theta*Q(v,total)
            rows.append((Q(1),tuple(b),Q(j+1)))
        m2=direct_copy_oracle(rows,d,2);rec=rectangular(rows)
        assert m2<=rec<=sharp_two_stamp_constant(k,theta)*m2
        general.append({"case":case,"k":k,"theta":str(theta),
                        "model":as_model(rows,d),"M2":str(m2),"R":str(rec)})
    assert sharp_two_stamp_constant(1,Q(1,2))==1
    assert sharp_two_stamp_constant(2,Q(1,2))==Q(4,3)
    return records,general

def deletion_tests():
    results=[]
    # All graphs on up to four vertices, all relevant stamp counts.
    for n in range(1,5):
        pairs=list(combinations(range(n),2))
        for mask in range(1<<len(pairs)):
            edges=[e for i,e in enumerate(pairs) if mask>>i&1]
            rows=coloring_rows(n,edges)
            low=[];high=[]
            for a,b,w in rows:
                radius=sum(map(abs,b),Q(0));largest=w/(a-radius)
                nonzero=[abs(v) for v in b if v]
                low.append(largest-w/(a-radius+2*min(nonzero)) if nonzero else Q(0))
                high.append(largest-w/(a+radius))
            rec=rectangular(rows)
            for r in range(1,n+1):
                m,_=stamped(rows,len(edges),r)
                tau_low=tau_high=None
                for deleted in range(1<<n):
                    kept=[v for v in range(n) if not deleted>>v&1]
                    rank={v:i for i,v in enumerate(kept)}
                    induced=[(rank[u],rank[v]) for u,v in edges if u in rank and v in rank]
                    if colorable(len(kept),induced,r):
                        a=sum((low[v] for v in range(n) if deleted>>v&1),Q(0))
                        b=sum((high[v] for v in range(n) if deleted>>v&1),Q(0))
                        tau_low=a if tau_low is None else min(tau_low,a)
                        tau_high=b if tau_high is None else min(tau_high,b)
                assert tau_low<=rec-m<=tau_high
                results.append({"n":n,"edge_mask":mask,"stamps":r,
                                "lower":str(tau_low),"deficit":str(rec-m),"upper":str(tau_high)})
    return results


def compositions(total, length):
    if length==1:
        yield (total,)
    else:
        for first in range(total+1):
            for tail in compositions(total-first,length-1):
                yield (first,)+tail

def _matrix_rank(matrix):
    """Exact rational rank for the small spectral certificate matrices."""
    work=[list(map(Q,row)) for row in matrix]
    if not work:
        return 0
    rows,columns=len(work),len(work[0])
    pivot_row=0
    for column in range(columns):
        pivot=next((i for i in range(pivot_row,rows) if work[i][column]),None)
        if pivot is None:
            continue
        work[pivot_row],work[pivot]=work[pivot],work[pivot_row]
        scale=work[pivot_row][column]
        work[pivot_row]=[x/scale for x in work[pivot_row]]
        for i in range(rows):
            if i!=pivot_row and work[i][column]:
                factor=work[i][column]
                work[i]=[a-factor*b for a,b in zip(work[i],work[pivot_row])]
        pivot_row+=1
        if pivot_row==rows:
            break
    return pivot_row


def five_stamp_structure_tests():
    """Independent exact checks for the r=5 spectral and finite formulas."""
    universe=frozenset(range(5))
    patterns=[];splits=[]
    for bits in product((0,1),repeat=4):
        if not any(bits):
            continue
        pattern=(0,)+bits
        negative=frozenset(i+1 for i,bit in enumerate(bits) if bit)
        other=universe-negative
        side=negative if len(negative)<=2 else other
        patterns.append(pattern);splits.append(side)
    assert len(patterns)==len(set(splits))==15
    assert sum(len(side)==1 for side in splits)==5
    assert sum(len(side)==2 for side in splits)==10
    for i,first in enumerate(patterns):
        for j,second in enumerate(patterns):
            actual=len(set(zip(first,second)))
            if i==j:
                expected=2
            elif len(splits[i])==len(splits[j])==2 and len(splits[i]&splits[j])==1:
                expected=4
            else:
                expected=3
            assert actual==expected

    edges=tuple(combinations(range(5),2))
    adjacency=[[int(i!=j and len(set(edges[i])&set(edges[j]))==1)
                for j in range(len(edges))] for i in range(len(edges))]
    incidence=[[int(vertex in edge) for edge in edges] for vertex in range(5)]
    # A=B^T B-2I, BB^T=3I+J.  The exact ranks certify multiplicities
    # 1,4,5 for the eigenvalues 6,1,-2 of the line graph L(K_5).
    for i in range(10):
        for j in range(10):
            gram=sum(incidence[v][i]*incidence[v][j] for v in range(5))
            assert adjacency[i][j]==gram-(2 if i==j else 0)
    for i in range(5):
        for j in range(5):
            gram=sum(incidence[i][e]*incidence[j][e] for e in range(10))
            assert gram==(4 if i==j else 1)
    assert _matrix_rank(incidence)==5
    assert _matrix_rank([[adjacency[i][j]-(6 if i==j else 0)
                          for j in range(10)] for i in range(10)])==9
    assert _matrix_rank([[adjacency[i][j]-(1 if i==j else 0)
                          for j in range(10)] for i in range(10)])==6
    assert _matrix_rank([[adjacency[i][j]+(2 if i==j else 0)
                          for j in range(10)] for i in range(10)])==5
    uniform=Q(1,10)
    expected_N=sum((uniform*uniform*(2 if i==j else 4 if adjacency[i][j] else 3)
                    for i in range(10) for j in range(10)),Q(0))
    assert expected_N==Q(7,2)
    star=[i for i,e in enumerate(edges) if 0 in e]
    star_N=sum((Q(1,16)*(2 if i==j else 4 if adjacency[i][j] else 3)
                for i in star for j in star),Q(0))
    assert star_N==Q(7,2)

    constructions=[]
    edge_index={edge:i for i,edge in enumerate(edges)}
    for d in range(2,41):
        counts=[0]*10
        if d==2:
            counts[edge_index[(0,1)]]=1
            counts[edge_index[(0,2)]]=1
        elif d%4!=2:
            q,remainder=divmod(d,4)
            for offset,edge in enumerate(((0,1),(0,2),(0,3),(0,4))):
                counts[edge_index[edge]]=q+(offset<remainder)
        else:
            q=(d-2)//4
            assert q>=1
            for edge in combinations(range(4),2):
                counts[edge_index[edge]]+=1
            for edge in ((0,1),(0,2),(0,3),(0,4)):
                counts[edge_index[edge]]+=q-1
        assert sum(counts)==d and all(count>=0 for count in counts)
        pattern_sum=0
        for i,count in enumerate(counts):
            pattern_sum+=2*count*(count-1)//2
            for j in range(i+1,10):
                value=4 if adjacency[i][j] else 3
                pattern_sum+=value*count*counts[j]
        expected=4 if d==2 else (7*d*d)//4-d
        assert pattern_sum==expected
        constructions.append({"dimension":d,"maximum_pattern_sum":expected,
                              "edge_class_counts":counts})
    return {"split_classes":15,"singleton_splits":5,"two_splits":10,
            "line_graph_vertices":10,"line_graph_degree":6,
            "line_graph_spectrum":{"6":1,"1":4,"-2":5},
            "expected_patterns":"7/2","constructions":constructions}


def palette_tests():
    records=[];matrices=[]
    for r in (2,3,4,5):
        # Complement quotient: every column starts with zero and is nonconstant.
        patterns=[(0,)+bits for bits in product((0,1),repeat=r-1) if any(bits)]
        N=[[len(set(zip(u,v))) for v in patterns] for u in patterns]
        matrices.append({"stamps":r,"patterns":patterns,"pattern_counts":N})
        dimensions=range(2,11) if r<5 else range(2,8)
        for d in dimensions:
            best=-1;winner=None
            for counts in compositions(d,len(patterns)):
                # Ordered-pair sum includes d diagonal self-pairs, each of value 2.
                ordered=sum(counts[i]*counts[j]*N[i][j]
                            for i in range(len(patterns)) for j in range(len(patterns)))
                score=(ordered-2*d)//2
                if score>best: best=score;winner=counts
            pairs=d*(d-1)//2
            turan=(d*d)//3
            if r==2:
                expected=2*pairs
            elif r==3:
                expected=2*pairs+turan
            elif r==4:
                expected=2*pairs+2*turan
            else:
                expected=4 if d==2 else (7*d*d)//4-d
            assert best==expected
            records.append({"dimension":d,"stamps":r,"maximum_pattern_sum":best,
                            "column_class_counts":winner,"pairs":pairs})
    checks=[]
    rng=random.Random(SEED+3)
    for case in range(24):
        d=1+case%4;theta=Q(1+case%3,4)
        rows=[]
        for j in range(1+case%6):
            support=rng.sample(range(d),rng.randint(0,min(2,d)))
            raw=[rng.randint(1,5) for _ in support];total=sum(raw)
            b=[Q(0)]*d
            for coord,v in zip(support,raw):
                b[coord]=rng.choice((-1,1))*theta*Q(v,total)
            rows.append((Q(1),tuple(b),Q(j+1)))
        rec=rectangular(rows)
        for r in (3,4,5):
            exact,_=stamped(rows,d,r)
            assert exact<=rec<=support_two_constant(r,theta)*exact
            checks.append({"case":case,"stamps":r,"theta":str(theta),
                           "model":as_model(rows,d),"Mr":str(exact),"R":str(rec)})
    # Direct comparison, without the complement quotient or count formulas.
    small=[]
    for d in (2,3):
        rows=[]
        for i,j in combinations(range(d),2):
            for u,v in product((-1,1),repeat=2):
                b=[Q(0)]*d;b[i]=Q(u,4);b[j]=Q(v,4)
                rows.append((Q(1),tuple(b),Q(1)))
        for r in (2,3,4,5):
            actual=direct_copy_oracle(rows,d,r)
            C=d*(d-1)//2
            T=(d*d)//3
            if r==2:
                S=2*C
            elif r==3:
                S=2*C+T
            elif r==4:
                S=2*C+2*T
            else:
                S=4 if d==2 else (7*d*d)//4-d
            expected=4*C+S # theta/(1-theta)=1 at theta=1/2
            assert actual==expected
            small.append({"dimension":d,"stamps":r,"exact_load":str(actual)})
    return matrices,records,checks,small


def general_palette_tests():
    evaluations=[]; inequalities=[]; sampling=[]
    for k in (1,2,3):
        for r in (1,2,3):
            palette=[(1,)+tail for tail in product((-1,1),repeat=r-1)]
            distribution={u:Q(1,len(palette)) for u in palette}
            g=palette_average(k,r,Q(1,2),distribution)
            if r==1:
                assert g==h(k,Q(1,2))
            if r==2:
                alternate={(1,-1):Q(1)}
                assert palette_average(k,r,Q(1,2),alternate)==h_antipodal(k,Q(1,2))
                assert g<=h_antipodal(k,Q(1,2))
            evaluations.append({"k":k,"stamps":r,"theta":"1/2","G":str(g),
                                "columns":[{"column":u,"mass":str(p)} for u,p in distribution.items()]})
    rng=random.Random(SEED+4)
    for index in range(12):
        d=1+index%3;k=1+index%3;r=2+index%2;theta=Q(1,2)
        palette=[(1,)+tail for tail in product((-1,1),repeat=r-1)]
        distribution={u:Q(1,len(palette)) for u in palette}
        rows=[]
        for row in range(1+index%4):
            support=rng.sample(range(d),rng.randint(0,min(k,d)))
            b=[Q(0)]*d
            for i in support:
                b[i]=rng.choice((-1,1))*theta*Q(rng.randint(1,3),3*max(1,len(support)))
            rows.append((Q(1),tuple(b),Q(row+1)))
        g=palette_average(k,r,theta,distribution)
        mr,_=stamped(rows,d,r);rec=rectangular(rows)
        assert rec*(1-theta)*g<=mr
        inequalities.append({"k":k,"stamps":r,"theta":str(theta),"model":as_model(rows,d),
                              "G":str(g),"Mr":str(mr),"R":str(rec)})
    for d in (3,4,5):
        for k in (2,3):
            r=3;theta=Q(1,2)
            matrix=[[rng.choice((-1,1)) for _ in range(d)] for _ in range(r)]
            counts={}
            for i in range(d):
                column=tuple(matrix[j][i]*matrix[0][i] for j in range(r))
                counts[column]=counts.get(column,0)+1
            distribution={u:Q(count,d) for u,count in counts.items()}
            g=palette_average(k,r,theta,distribution)
            total=Q(0);n=0
            for support in combinations(range(d),k):
                for signs in product((-1,1),repeat=k):
                    # Direct family evaluation, not the palette kernel.
                    total+=max(1/(1+theta*sum((Q(signs[i]*matrix[j][coord],k)
                        for i,coord in enumerate(support)),Q(0))) for j in range(r))
                    n+=1
            hd=total/n
            upper=Q(k*(k-1),2*d)*(1/(1-theta)-1/(1+theta))
            assert abs(hd-g)<=upper
            sampling.append({"dimension":d,"k":k,"stamps":r,"matrix":matrix,
                             "H":str(hd),"G":str(g),"absolute_gap":str(abs(hd-g)),
                             "proved_upper":str(upper)})
    return evaluations,inequalities,sampling

def run_all():
    general_evaluations,general_inequalities,general_sampling=general_palette_tests()
    sharp,random_cases=sharp_tests()
    palettes,palette_extrema,palette_random,palette_direct=palette_tests()
    five_stamp=five_stamp_structure_tests()
    sharp_two,random_two=two_stamp_tests()
    deletion=deletion_tests()
    cuts=maxcut_tests()
    stamps,direct=stamp_tests()
    fixed_r_reductions=fixed_r_saturation_reduction_tests()
    covering,minimum=covering_tests()
    model,cert,rejected,boundary=certificate_tests()
    certificate_oracles=certificate_oracle_tests()
    transition_count,transitions=transition_tests()
    contractions=contraction_tests()
    assert sharp_constant(2,Q(1,2))==Q(12,7)>Q(3,2)
    clipping_rows=[(Q(2),(Q(1),Q(0)),Q(1)),
                   (Q(2),(Q(0),Q(1)),Q(1)),
                   (Q(2),(Q(-1,2),Q(-1,2)),Q(4))]
    zero_cases=[]
    for k in range(1,7):
        rows=allsign_rows(k,Q(0))
        m=coherent(rows,k)[0];rec=rectangular(rows)
        assert m==rec==2**k
        assert sharp_constant(k,Q(0))==sharp_two_stamp_constant(k,Q(0))==1
        zero_cases.append({"k":k,"theta":"0","M1":str(m),"R":str(rec),"K1":"1","K2":"1"})
    p=Q(4,3);epsilon=Q(1,8)
    assert p-Q(1,2)*(1-1/p)+epsilon==p and 1/p==Q(3,4)
    raw_latent=(Q(2),Q(0))
    raw_prices=tuple(a+sum((b[i]*raw_latent[i] for i in range(2)),Q(0)) for a,b,w in clipping_rows)
    clipped_prices=tuple(min(Q(3),max(Q(1),q)) for q in raw_prices)
    clipped_load=sum((row[2]/q for row,q in zip(clipping_rows,clipped_prices)),Q(0))
    assert raw_prices==(4,2,1) and clipped_prices==(3,2,1) and clipped_load==Q(29,6)
    clipping_M=coherent(clipping_rows,2)[0]
    assert clipping_M==Q(14,3)<Q(19,4)<Q(29,6)
    assert sum((value(row,(1,0)) for row in clipping_rows),Q(0))==Q(7,2)
    return {
      "zero_radius_boundaries":zero_cases,
      "clipping_negative_control":{"model":as_model(clipping_rows,2),
        "raw_latent":["2","0"],"raw_prices":["4","2","1"],
        "row_clipped_prices":["3","2","1"],"row_clipped_load":"29/6",
        "latent_clipped_load":"7/2","M1":"14/3","capacity":"19/4"},
      "counts":{"zero_radius_cases":len(zero_cases),"general_palette_evaluations":len(general_evaluations),
                "general_palette_inequalities":len(general_inequalities),
                "sampling_comparisons":len(general_sampling),"palette_extrema":len(palette_extrema),"palette_general_cases":len(palette_random),
                "palette_direct_checks":len(palette_direct),
                "five_stamp_constructions":len(five_stamp["constructions"]),
                "five_stamp_spectral_certificates":1,
                "two_stamp_extremizers":len(sharp_two),"two_stamp_general_cases":len(random_two),
                "weighted_deletion_cases":len(deletion),"sharp_extremizers":len(sharp),"general_rational_instances":len(random_cases),
                "maxcut_graphs":len(cuts),"coloring_stamp_cases":len(stamps),
                "fixed_r_saturation_reductions":len(fixed_r_reductions),
                "independent_copy_oracles":len(direct),"covering_constructions":len(covering),
                "exact_covering_minima":len(minimum),"rejected_certificate_mutations":len(rejected),
                "boundary_certificates":len(boundary),
                "certificate_oracle_cases":len(certificate_oracles),"transition_orders":transition_count,
                "contraction_schedules":len(contractions)},
      "general_palette_evaluations":general_evaluations,
      "general_palette_inequalities":general_inequalities,"general_sampling":general_sampling,
      "palettes":palettes,"palette_extrema":palette_extrema,
      "five_stamp_structure":five_stamp,
      "palette_random":palette_random,"palette_direct":palette_direct,
      "sharp_two":sharp_two,"random_two":random_two,"deletion":deletion,
      "sharp":sharp,"random_cases":random_cases,"maxcut":cuts,"stamps":stamps,
      "fixed_r_saturation_reductions":fixed_r_reductions,"direct_copy":direct,
      "covering":covering,"covering_minima":minimum,"certificate_model":model,"certificate":cert,
      "rejected_mutations":rejected,"boundary_certificates_data":boundary,
      "certificate_oracles":certificate_oracles,"transitions":transitions,"contraction":contractions,
      "negative_controls":{"coherent_safe_load":"8/3","delayed_unsafe_load":"4","capacity":"3",
                           "false_scalar_factor":"3/2","dimension_two_factor":"12/7",
                           "persistent_bias_fixed_price":"4/3","biased_rate":"3/4"}}
