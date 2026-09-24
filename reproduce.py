#!/usr/bin/env python3
# PUBLIC-REPRODUCTION-WRAPPER
from __future__ import annotations
import subprocess,sys
from pathlib import Path
def main():
 core=Path(__file__).with_name('reproduce_core.py')
 try:p=subprocess.run([sys.executable,'-B',str(core),*sys.argv[1:]],text=True,capture_output=True,timeout=3600)
 except (OSError,subprocess.SubprocessError):
  print('REPRODUCTION FAILED: execution error',file=sys.stderr);return 2
 text=(p.stdout or '')+(p.stderr or '')
 if p.returncode and 'Traceback (most recent call last)' in text:
  # Preserve a bounded final diagnostic line without exposing an internal stack trace.
  tail='; '.join(x.strip() for x in text.splitlines()[-3:] if x.strip())[:1000]
  print('REPRODUCTION FAILED: '+(tail or 'comparison or execution error'),file=sys.stderr);return p.returncode or 2
 if p.stdout:sys.stdout.write(p.stdout)
 if p.stderr:sys.stderr.write(p.stderr)
 return p.returncode
if __name__=='__main__':raise SystemExit(main())
