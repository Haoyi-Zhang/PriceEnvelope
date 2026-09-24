#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
PAYLOADS=[
 ('empty',b''),('truncated',b'{'),('nan',b'{"x":NaN}'),('duplicate-key',b'{"x":1,"x":2}'),
 ('invalid-utf8',b'\xff\xfe'),('bom',b'\xef\xbb\xbf{}'),('nul',b'{"x":"\x00"}'),
 ('array',b'[]'),('null',b'null'),('boolean',b'true'),('number',b'1'),('empty-object',b'{}'),
 ('huge-exponent',b'{"x":1e999999}'),('prototype-key',b'{"__proto__":{}}'),
 ('deep',b'{"x":['*100+b'0'+b']}'*100+b'}'),('oversized-string',b'{"x":"'+b'a'*(9*1024*1024)+b'"}')]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--checker',type=Path,default=Path('check_certificate.py')); ap.add_argument('--model',type=Path,default=Path('results/certificate_model.json')); ap.add_argument('--certificate',type=Path,default=Path('results/certificate.json')); ns=ap.parse_args()
 root=Path.cwd(); checker=(root/ns.checker).resolve(); model=(root/ns.model).resolve(); cert=(root/ns.certificate).resolve()
 assert checker.exists() and model.exists() and cert.exists()
 records=[]
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for name,payload in PAYLOADS:
   bad=td/(name+'.json'); bad.write_bytes(payload)
   for slot in ('model','certificate'):
    cmd=[sys.executable,'-B',str(checker),str(bad if slot=='model' else model),str(bad if slot=='certificate' else cert),'--capacity','9/2']
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=20)
    text=(p.stdout or '')+(p.stderr or '')
    assert p.returncode!=0,(name,slot,text)
    assert 'Traceback' not in text,(name,slot,text)
    assert len(text)<20000,(name,slot,len(text))
    records.append({'case':name,'slot':slot,'returncode':p.returncode})
 print(json.dumps({'payload_classes':len(PAYLOADS),'black_box_rejections':len(records),'status':'PASS'}))
if __name__=='__main__': main()
