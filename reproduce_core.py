#!/usr/bin/env python3
"""Run all finite checks once, or compare a clean run to delivered exact results."""
from pathlib import Path
import argparse
import csv
import json
import resource
import sys
import time
from tests.validate import run_all
from tests.control_pipeline import run_pipeline
from tests.correlated_pipeline import run_correlated_pipeline
from tests.variational import run_variational
from tests.reference_audit import run_reference_audit
from export_figures import export

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("results"))
    parser.add_argument("--check-against",type=Path)
    args=parser.parse_args()
    # Single process, bounded memory and CPU; no child processes or network calls.
    resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    start=time.perf_counter();cpu=time.process_time()
    result=run_all()
    result["reference_audit"]=run_reference_audit()
    result["control_pipeline"]=run_pipeline()
    result["correlated_pipeline"]=run_correlated_pipeline()
    variational=run_variational()
    result["variational_grids"]=variational["grids"]
    result["support_two_sandwich"]=variational["support_two_sandwich"]
    result["counts"].update({"controller_runs":result["control_pipeline"]["run_count"],
        "controller_slots":result["control_pipeline"]["slots"],
        "controller_intermediate_states":result["control_pipeline"]["intermediate_states"],
        "correlated_epochs":result["correlated_pipeline"]["epochs"],
        "correlated_transitions":result["correlated_pipeline"]["transition_count"],
        "correlated_intermediate_states":result["correlated_pipeline"]["intermediate_states"],
        "correlated_stamp_tuples":result["correlated_pipeline"]["oracle_stamp_tuples"],
        "variational_grids":len(result["variational_grids"]),
        "support_two_sandwich_checks":len(result["support_two_sandwich"]),
        "scholarly_references":result["reference_audit"]["scholarly_references"],
        "literature_calibration_rows":result["reference_audit"]["literature_calibration_rows"]})
    # Compare the actual JSON representation, not Python tuple/list distinctions.
    exact_text=json.dumps(result,indent=2)+"\n"
    if args.check_against:
        expected=json.loads((args.check_against/"exact_results.json").read_text())
        if expected!=json.loads(exact_text):
            raise AssertionError("exact result content differs from delivered evidence")
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"exact_results.json").write_text(exact_text)
    (args.output/"reference_audit.json").write_text(
        json.dumps(result["reference_audit"],indent=2)+"\n")
    with (args.output/"sharp_constants.csv").open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=["k","theta","M1","R","ratio"])
        writer.writeheader();writer.writerows(result["sharp"])
    (args.output/"certificate_model.json").write_text(json.dumps(result["certificate_model"],indent=2)+"\n")
    (args.output/"certificate.json").write_text(json.dumps(result["certificate"],indent=2)+"\n")
    (args.output/"control_pipeline.json").write_text(json.dumps(result["control_pipeline"],indent=2)+"\n")
    (args.output/"correlated_pipeline.json").write_text(
        json.dumps(result["correlated_pipeline"],indent=2)+"\n")
    export(args.output, result["control_pipeline"])
    # Measure through serialization, comparison, and export, not only the assertions.
    usage=resource.getrusage(resource.RUSAGE_SELF)
    metrics={"wall_seconds":time.perf_counter()-start,"cpu_seconds":time.process_time()-cpu,
             "peak_rss_kib":usage.ru_maxrss,"reported_swaps":usage.ru_nswap,"workers":1,
             "exit_status":0}
    (args.output/"run_metrics.json").write_text(json.dumps(metrics,indent=2)+"\n")
    print(json.dumps({"counts":result["counts"],"metrics":metrics},indent=2))

if __name__=="__main__":
    try: main()
    except Exception as exc:
        print(f"VALIDATION FAILED: {type(exc).__name__}: {exc}",file=sys.stderr)
        sys.exit(1)
