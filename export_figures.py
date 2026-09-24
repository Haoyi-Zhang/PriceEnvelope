#!/usr/bin/env python3
"""Export rational theorem evaluations and their decimal plotting coordinates."""
from pathlib import Path
from fractions import Fraction as Q
import argparse
import csv
import json

def export(destination: Path, pipeline=None) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with (destination/'reserve-factors.csv').open('w', newline='') as out:
        w=csv.writer(out)
        w.writerow(['theta','K21','K22','K23','K24','K25','theta_exact','K21_exact','K22_exact','K23_exact','K24_exact','K25_exact'])
        for i in range(20):
            t=Q(i,20)
            values=[t,2*(1+t)/(2-t*t),2/(2-t),3/(3-t),6/(6-t),8/(8-t)]
            w.writerow([format(float(x),'.14g') for x in values]+[str(x) for x in values])

    if pipeline is None:
        source=Path(__file__).resolve().parent/'results'/'control_pipeline.json'
        if source.exists():
            pipeline=json.loads(source.read_text())
    if pipeline is not None:
        selected=[run for run in pipeline['runs'] if run['delay']==2 and run['start']==['4/5','1']]
        series={run['grid_mode']:run['records'] for run in selected}
        if set(series)!={'constant','vanishing'}:
            raise ValueError('expected the two declared controller plot cases')
        with (destination/'controller-errors.csv').open('w',newline='') as out:
            w=csv.writer(out);w.writerow(['slot','constant','vanishing','constant_bound','vanishing_bound'])
            for a,b in zip(series['constant'],series['vanishing']):
                w.writerow([a['slot']+1]+[format(float(Q(v)),'.14g') for v in
                    (a['state_error'],b['state_error'],a['state_bound'],b['state_bound'])])

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('results'))
    args=parser.parse_args()
    export(args.output)
