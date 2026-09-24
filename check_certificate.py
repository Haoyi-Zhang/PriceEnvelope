#!/usr/bin/env python3
# PUBLIC-CHECKER-HARDENING-WRAPPER
from __future__ import annotations
import json, os, re, stat, subprocess, sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
MAX_BYTES=8*1024*1024; MAX_DEPTH=80; MAX_ITEMS=250000; MAX_STRING=2*1024*1024; MAX_NUMBER_CHARS=512
class InputError(ValueError): pass

def _pairs(xs):
 out={}
 for k,v in xs:
  if k in out: raise InputError('duplicate JSON key')
  out[k]=v
 return out

def _constant(x): raise InputError('non-finite JSON constant')
def _int(x):
 if len(x)>MAX_NUMBER_CHARS: raise InputError('integer token too long')
 return int(x)
def _float(x):
 if len(x)>MAX_NUMBER_CHARS: raise InputError('numeric token too long')
 try: d=Decimal(x)
 except InvalidOperation: raise InputError('invalid numeric token')
 if not d.is_finite(): raise InputError('non-finite numeric token')
 return d

def _walk(x,depth=0,budget=None):
 if budget is None: budget=[0]
 if depth>MAX_DEPTH: raise InputError('JSON nesting too deep')
 budget[0]+=1
 if budget[0]>MAX_ITEMS: raise InputError('JSON container too large')
 if isinstance(x,str) and len(x)>MAX_STRING: raise InputError('JSON string too long')
 if isinstance(x,dict):
  for k,v in x.items(): _walk(k,depth+1,budget); _walk(v,depth+1,budget)
 elif isinstance(x,list):
  for v in x: _walk(v,depth+1,budget)
 return x

def strict_file(arg):
 p=Path(arg)
 try: st=p.lstat()
 except OSError as e: raise InputError('input file unavailable') from e
 if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode): raise InputError('input must be a regular non-symlink file')
 if st.st_size>MAX_BYTES: raise InputError('input file too large')
 raw=p.read_bytes()
 if raw.startswith(b'\xef\xbb\xbf'): raise InputError('UTF-8 BOM is not accepted')
 if b'\x00' in raw: raise InputError('NUL byte is not accepted')
 try: txt=raw.decode('utf-8','strict')
 except UnicodeDecodeError as e: raise InputError('input is not strict UTF-8') from e
 try: obj=json.loads(txt,object_pairs_hook=_pairs,parse_constant=_constant,parse_int=_int,parse_float=_float)
 except (json.JSONDecodeError,InputError,ValueError,OverflowError) as e: raise InputError('invalid JSON: '+str(e)[:200]) from e
 _walk(obj); return obj

def main():
 if len(sys.argv)<3:
  print('REJECTED: expected MODEL CERTIFICATE [options]',file=sys.stderr); return 2
 try: strict_file(sys.argv[1]); strict_file(sys.argv[2])
 except InputError as e:
  print('REJECTED: invalid input: '+str(e),file=sys.stderr); return 2
 core=Path(__file__).with_name('check_certificate_core.py')
 try:
  p=subprocess.run([sys.executable,'-B',str(core),*sys.argv[1:]],text=True,capture_output=True,timeout=120)
 except (OSError,subprocess.SubprocessError) as e:
  print('REJECTED: checker execution failed',file=sys.stderr); return 2
 combined=(p.stdout or '')+(p.stderr or '')
 if 'Traceback (most recent call last)' in combined:
  print('REJECTED: invalid model or certificate',file=sys.stderr); return p.returncode or 2
 if p.stdout: sys.stdout.write(p.stdout)
 if p.stderr: sys.stderr.write(p.stderr)
 return p.returncode
if __name__=='__main__': raise SystemExit(main())
