from fractions import Fraction as Q
from itertools import product, combinations
from math import comb
from time import perf_counter, process_time
import json, resource

t0=perf_counter(); cpu0=process_time()
def signs(d): return list(product((-1,1), repeat=d))
def val(f,z):
 a,b,w=f
 return w/(a+sum((c*v for c,v in zip(b,z)),Q(0)))
def maximum(fs,d): return max(sum((val(f,z) for f in fs),Q(0)) for z in signs(d))
def rectangle(fs): return sum((w/(a-sum(map(abs,b),Q(0))) for a,b,w in fs),Q(0))
def h(d,t): return sum((Q(comb(d,j),2**d)/(1+t*Q(2*j-d,d)) for j in range(d+1)),Q(0))
sharp=[]
for d in range(1,6):
 for t in (Q(1,4),Q(1,2),Q(3,4)):
  fs=[(Q(1),tuple(t*Q(s,d) for s in z),Q(1)) for z in signs(d)]
  m=maximum(fs,d); rec=rectangle(fs); k=1/((1-t)*h(d,t))
  assert rec/m==k
  sharp.append(dict(d=d,theta=str(t),coherent=str(m),rectangular=str(rec),ratio=str(k)))
maxcut_cases=0
for n in range(1,5):
 edges=list(combinations(range(n),2))
 for bits in product((0,1),repeat=len(edges)):
  es=[e for e,v in zip(edges,bits) if v]
  fs=[]
  for u,v in es:
   b=[Q(0)]*n;b[u]=Q(1,2);b[v]=-Q(1,2)
   fs.extend([(Q(4),tuple(b),Q(30)),(Q(4),tuple(-x for x in b),Q(30))])
  cut=max(sum(z[u]!=z[v] for u,v in es) for z in signs(n))
  assert maximum(fs,n)==15*len(es)+cut
  maxcut_cases+=1
# Counterexamples test the information contract and the false dimension-free k=1 bound.
fs=[(Q(1),(Q(1,2),),Q(1)),(Q(1),(Q(-1,2),),Q(1))]
coherent=maximum(fs,1); rec=rectangle(fs)
assert coherent==Q(8,3) and rec==4 and coherent<3<rec
assert sharp[4]['ratio']=='12/7' and Q(sharp[4]['ratio'])>Q(3,2)
report={'sharp_instances':len(sharp),'maxcut_instances':maxcut_cases,
 'negative_controls':{'coherent_envelope':str(coherent),'two_stamp_envelope':str(rec),'capacity':'3','false_scalar_bound_rejected':True},
 'sharp_values':sharp,'wall_seconds':perf_counter()-t0,'cpu_seconds':process_time()-cpu0,
 'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'reported_swaps':resource.getrusage(resource.RUSAGE_SELF).ru_nswap,'workers':1}
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description='Exact intake pilot; finite checks only.')
parser.add_argument('--output',type=Path,default=Path('pilot.json'))
args=parser.parse_args()
args.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
