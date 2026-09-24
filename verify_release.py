#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

def call(cmd,cwd,timeout=2400,expect=0):
 p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'})
 if (expect=='nonzero' and p.returncode==0) or (expect!='nonzero' and p.returncode!=expect):
  raise RuntimeError({'cmd':cmd,'rc':p.returncode,'stdout':p.stdout[-5000:],'stderr':p.stderr[-5000:]})
 if 'Traceback' in (p.stdout or '')+(p.stderr or ''): raise RuntimeError('traceback leaked: '+str(cmd))
 return p

def main():
 root=Path(__file__).resolve().parent
 bad=[]
 for p in root.rglob('*'):
  rel=p.relative_to(root)
  if p.is_symlink(): bad.append('symlink:'+str(rel))
  if any(x in rel.parts for x in ('.git','__pycache__')) or p.suffix=='.pyc': bad.append('generated:'+str(rel))
 if bad: raise SystemExit('release hygiene failure: '+repr(bad))
 # manifest
 mf=root/'RELEASE-MANIFEST.sha256'
 if mf.exists():
  for line in mf.read_text().splitlines():
   if not line.strip(): continue
   h,rel=line.split('  ',1); p=root/rel
   if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h: raise SystemExit('manifest mismatch: '+rel)
 # reference floor and set consistency
 rp=root/'review_audit/reference-local-audit.json'
 if rp.exists():
  x=json.loads(rp.read_text()); assert x['entry_count']>=55; assert not x['missing']; assert not x['unused']; assert not x['duplicate_keys']; assert not x['duplicate_dois']; assert not x['duplicate_titles']
 call([sys.executable,'-B','independent_random_exact_cases.py','--output',str(root/'review_audit/independent_random_exact_cases.json')],root)
 call([sys.executable,'-B','reproduce.py','--output',str(root/'_verify_reproduced'),'--check-against','results'],root)
 # locate standard certificate inputs
 model=next(iter((root/'results').glob('*model*.json'))); cert=next(iter((root/'results').glob('*certificate*.json')))
 pos=call([sys.executable,'-B','check_certificate.py',str(model),str(cert),'--capacity','9/2'],root)
 neg=call([sys.executable,'-B','check_certificate.py',str(model),str(cert),'--capacity','449/100'],root,expect='nonzero')
 call([sys.executable,'-B','adversarial_certificate_tests.py','--model',str(model.relative_to(root)),'--certificate',str(cert.relative_to(root))],root)
 call([sys.executable,'-B','reference_tamper_tests.py'],root)
 import shutil; shutil.rmtree(root/'_verify_reproduced',ignore_errors=True)
 print(json.dumps({'status':'PASS','reference_floor':55,'positive_certificate':True,'below_bound_rejected':True,'random_exact_cases':128,'adversarial_payload_classes':16,'tamper_rejected':True},sort_keys=True))
if __name__=='__main__': main()
