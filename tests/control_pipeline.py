"""Exact, bounded commanded-rate pipeline for the manuscript's two-link example.

This is a deterministic mathematical controller, not a packet-network simulator.
Both constant and vanishing quantization error are retained; no speedup target.
"""
from fractions import Fraction as Q

A=((1,0,1),(0,1,1))
WEIGHTS=(Q(4),Q(4),Q(1))
CAP=(Q(5),Q(5))
OPT_P=(Q(9,10),Q(9,10))
OPT_X=(Q(40,9),Q(40,9),Q(5,9))
RHO=Q(265,512)
LOWER=Q(4,5)
UPPER=Q(1)
LIP=(Q(50,9),Q(50,9),Q(25,36))
KAPPA=(Q(10,9),Q(10,9),Q(10,9))
LAMBDA=Q(5,4)


def grid(slot, mode):
    return Q(1,2**(12+(slot//8 if mode=='vanishing' else 0)))


def price_error(p):
    return max(abs(p[i]-OPT_P[i]) for i in range(2))


def rate_at(p,s):
    return WEIGHTS[s]/sum(A[i][s]*p[i] for i in range(2))


def check_rates(x):
    assert all(v>0 for v in x)
    assert all(sum(A[i][s]*x[s] for s in range(3))<=CAP[i] for i in range(2))


def run_pipeline(steps=64):
    if type(steps) is not int or not 1<=steps<=128:
        raise ValueError('pipeline steps must be an integer in [1,128]')
    assert all(sum(A[i][s]*OPT_X[s] for s in range(3))==CAP[i] for i in range(2))
    assert all(rate_at(OPT_P,s)==OPT_X[s] for s in range(3))
    all_runs=[]
    total_transitions=0
    for delay in range(3):
        for start in ((Q(4,5),Q(1)),(Q(1),Q(4,5))):
            for mode in ('constant','vanishing'):
                history=[start]
                old=list(OPT_X)
                old_enclosure_error=Q(0)
                records=[]
                levels=[price_error(start)]
                horizon=delay+2
                while len(levels)<=steps//horizon+1:
                    j=len(levels)
                    value=RHO*levels[-1]+grid((j-1)*horizon,mode)
                    assert value<=levels[-1]
                    levels.append(value)
                for t in range(steps):
                    i=t%2
                    ages=[(t+j)%(delay+1) for j in range(2)]
                    read=[history[max(0,t-ages[j])][j] for j in range(2)]
                    grad=CAP[i]-Q(4)/read[i]-Q(1)/sum(read)
                    raw=read[i]-grad/Q(8)
                    spacing=grid(t,mode)
                    quantized=(raw//spacing)*spacing
                    err=quantized-raw
                    assert abs(err)<spacing
                    p=list(history[-1])
                    p[i]=min(UPPER,max(LOWER,quantized))
                    history.append(tuple(p))
                    assert price_error(p)<=levels[(t+1)//horizon]
                    active=history[max(0,t+1-delay):t+2]
                    lo=[min(q[j] for q in active) for j in range(2)]
                    hi=[max(q[j] for q in active) for j in range(2)]
                    enclosure_error=max(price_error(q) for q in active)
                    # Nonnegative independent price intervals: one lower corner
                    # simultaneously maximizes every row. No correlation gain.
                    maximum_rates=[rate_at(lo,s) for s in range(3)]
                    envelopes=[sum(A[j][s]*maximum_rates[s] for s in range(3)) for j in range(2)]
                    gamma=min([Q(1)]+[CAP[j]/envelopes[j] for j in range(2)])
                    assert gamma>=1/(1+LAMBDA*enclosure_error)
                    source_stamps=[max(0,t+1-(t+s)%(delay+1)) for s in range(3)]
                    proposal=[rate_at(history[source_stamps[s]],s) for s in range(3)]
                    target=[gamma*q for q in proposal]
                    check_rates(target)
                    for s in range(3):
                        assert abs(target[s]-OPT_X[s])<=(LIP[s]+LAMBDA*OPT_X[s])*enclosure_error
                    transition_error=max(old_enclosure_error,enclosure_error)
                    middle=[min(old[s],target[s]) for s in range(3)]
                    state=list(old)
                    order=[(t+s)%3 for s in range(3)]
                    for phase in (middle,target):
                        for s in order:
                            state[s]=phase[s]
                            check_rates(state)
                            for q in range(3):
                                lower=OPT_X[q]/((1+LAMBDA*transition_error)*(1+KAPPA[q]*transition_error))
                                assert state[q]>=lower
                            total_transitions+=1
                    assert state==target
                    old=target
                    old_enclosure_error=enclosure_error
                    records.append({'slot':t,'coordinate':i,'read_ages':ages,
                        'price':[str(v) for v in p], 'quantization_error':str(err),
                        'grid':str(spacing), 'state_error':str(price_error(p)),
                        'state_bound':str(levels[(t+1)//horizon]),
                        'price_lower':[str(v) for v in lo],'price_upper':[str(v) for v in hi],
                        'source_stamps':source_stamps,'enclosure_error':str(enclosure_error),
                        'envelopes':[str(v) for v in envelopes],'gamma':str(gamma),
                        'proposal':[str(v) for v in proposal],'target':[str(v) for v in target],
                        'application_order':order})
                all_runs.append({'delay':delay,'start':[str(v) for v in start],
                                 'grid_mode':mode,'steps':steps,'records':records})
    return {'runs':all_runs,'run_count':len(all_runs),'slots':len(all_runs)*steps,
            'intermediate_states':total_transitions,'rho':str(RHO)}
