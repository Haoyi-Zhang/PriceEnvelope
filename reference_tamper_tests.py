#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--reproduce',type=Path,default=Path('reproduce.py')); ap.add_argument('--reference',type=Path,default=Path('results')); ns=ap.parse_args()
 root=Path.cwd(); rep=(root/ns.reproduce).resolve(); ref=(root/ns.reference).resolve(); assert rep.exists() and ref.is_dir()
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); bad=td/'reference'; shutil.copytree(ref,bad)
  preferred=[bad/'exact_results.json',bad/'summary.json',bad/'results.json']
  p=next((x for x in preferred if x.exists()),None)
  if p is None:
   cs=sorted(bad.glob('*.json'),key=lambda x:x.stat().st_size,reverse=True); assert cs; p=cs[0]
  obj=json.loads(p.read_text())
  if isinstance(obj,dict):
   # mutate an existing scalar recursively when possible, to ensure the public comparator sees it.
   def mutate(x):
    if isinstance(x,dict):
     for k in sorted(x):
      y,ok=mutate(x[k]);
      if ok: x[k]=y; return x,True
    elif isinstance(x,list):
     for i,v in enumerate(x):
      y,ok=mutate(v)
      if ok: x[i]=y; return x,True
    elif isinstance(x,bool): return (not x),True
    elif isinstance(x,int): return x+1,True
    elif isinstance(x,float): return x+1.0,True
    elif isinstance(x,str) and x: return x+'-TAMPERED',True
    return x,False
   obj,ok=mutate(obj); assert ok
  elif isinstance(obj,list): obj.append({'tampered':True})
  else: obj={'original':obj,'tampered':True}
  p.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
  out=td/'out'
  q=subprocess.run([sys.executable,'-B',str(rep),'--output',str(out),'--check-against',str(bad)],cwd=root,text=True,capture_output=True,timeout=1800)
  text=(q.stdout or '')+(q.stderr or '')
  assert q.returncode!=0,(q.returncode,text)
  assert 'Traceback' not in text,text
 print(json.dumps({'tampered_file':p.name,'tampered_reference_rejected':True,'status':'PASS'}))
if __name__=='__main__': main()
