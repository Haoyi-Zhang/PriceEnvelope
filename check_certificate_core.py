#!/usr/bin/env python3
"""Validate a supplied rational separator certificate without running a solver."""
import argparse,json,sys
from src.checker import check,InvalidCertificate

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model");parser.add_argument("certificate")
    parser.add_argument("--capacity")
    args=parser.parse_args()
    with open(args.model) as f: model=json.load(f)
    with open(args.certificate) as f: certificate=json.load(f)
    value=check(model,certificate,args.capacity)
    print(f"CERTIFIED upper bound: {value}")

if __name__=="__main__":
    try: main()
    except (OSError,ValueError,InvalidCertificate) as exc:
        print(f"REJECTED: {exc}",file=sys.stderr);sys.exit(1)
