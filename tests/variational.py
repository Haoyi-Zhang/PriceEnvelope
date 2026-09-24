"""Small exact simplex grids: interval checks, not a scalable optimizer."""
from fractions import Fraction as Q
from itertools import product
from math import comb
from src.envelope import (palette_average, pair_pattern_count, qi_clique_columns,
                          qi_clique_size, sharp_constant, support_two_constant,
                          support_two_sandwich)

def compositions(total,bins):
    if bins==1:
        yield (total,)
        return
    for n in range(total+1):
        for rest in compositions(total-n,bins-1):
            yield (n,)+rest

def run_variational_grids():
    records=[]
    t=Q(1,2); k=2
    for r in range(1,6):
        columns=[(1,)+s for s in product((-1,1),repeat=r-1)]
        m=len(columns)
        kernel={}
        for i,u in enumerate(columns):
            for j,v in enumerate(columns):
                kernel[i,j]=sum((1/(1+t*Q(min(a*u[l]+b*v[l] for l in range(r)),2))
                                  for a,b in product((-1,1),repeat=2)),Q(0))/4
        true_K=sharp_constant(2,t) if r==1 else support_two_constant(r,t)
        true_G=1/((1-t)*true_K)
        for denominator in ([1,2,3,4,16,64] if r==2 else range(1,5)):
            best=Q(-1);winner=None;count=0
            for counts in compositions(denominator,m):
                value=sum((counts[i]*counts[j]*kernel[i,j] for i in range(m) for j in range(m)),Q(0))/denominator**2
                count+=1
                if value>best:
                    best,winner=value,counts
            assert count==comb(denominator+m-1,m-1)
            distribution={c:Q(n,denominator) for c,n in zip(columns,winner) if n}
            assert palette_average(k,r,t,distribution)==best
            upper=min(1/(1-t),best+Q(k*(m-1),denominator)*(1/(1-t)-1/(1+t)))
            assert best<=true_G<=upper
            interval=(1/((1-t)*upper),1/((1-t)*best))
            assert interval[0]<=true_K<=interval[1]
            noncollapse=1/(1-t/(2**(r-1)*(k*(1-t)+2*t)))
            assert true_K>=noncollapse>1
            records.append({'k':k,'stamps':r,'theta':str(t),'denominator':denominator,
                            'grid_points':count,'columns':columns,'counts':winner,
                            'G_lower':str(best),'G_upper':str(upper),
                            'K_lower':str(interval[0]),'K_upper':str(interval[1]),
                            'exact_K':str(true_K),'noncollapse_lower':str(noncollapse)})
    return records


def run_support_two_sandwich():
    """Attack the explicit all-stamp support-two sandwich with exact arithmetic."""
    records=[]
    previous_upper={}
    for stamps in range(4,9):
        columns=qi_clique_columns(stamps)
        clique=qi_clique_size(stamps)
        assert len(columns)==clique and len(set(columns))==clique
        for index, first in enumerate(columns):
            assert pair_pattern_count(first,first)==2
            for second in columns[index+1:]:
                assert pair_pattern_count(first,second)==4
        pattern_sum=sum((pair_pattern_count(first,second)
                         for first in columns for second in columns),0)
        beta=Q(pattern_sum,4*clique*clique)
        assert beta==1-Q(1,2*clique)
        for theta in (Q(1,4),Q(1,2),Q(3,4)):
            lower,upper=support_two_sandwich(stamps,theta)
            assert 1<lower<=upper
            if stamps in (4,5):
                exact=support_two_constant(stamps,theta)
                assert lower<=exact==upper
            else:
                exact=None
            if theta in previous_upper:
                assert upper<previous_upper[theta]
            previous_upper[theta]=upper
            records.append({'stamps':stamps,'theta':str(theta),
                            'clique_size':clique,'column_count':len(columns),
                            'beta_witness':str(beta),'K_lower':str(lower),
                            'K_upper':str(upper),
                            'exact_K_if_known':None if exact is None else str(exact)})
    return records


def run_variational():
    return {'grids':run_variational_grids(),
            'support_two_sandwich':run_support_two_sandwich()}

