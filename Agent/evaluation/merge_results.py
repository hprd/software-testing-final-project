#!/usr/bin/env python3
"""Combine distinct evaluation runs without overwriting or duplicating evidence."""
import argparse, json, pathlib

def merge(paths):
 results=[];seen=set();sources=[];metadata=[]
 for path in paths:
  data=json.loads(path.read_text());sources.append({'path':str(path),'complete':data.get('complete')});metadata.append(data.get('metadata') or {})
  for row in data['results']:
   if row['id'] in seen:raise ValueError('duplicate case ID: '+row['id'])
   seen.add(row['id']);results.append(row)
 keys=('model','endpoint','cases_sha256','resolved_sha256','reviewer_sha256','constraint_check')
 same=all(metadata[0].get(k) is not None and all(m.get(k)==metadata[0][k] for m in metadata) for k in keys)
 common={k:metadata[0][k] for k in keys} if same else {}
 return {'sources':sources,'metadata':common,'results':results,'complete':all(x['complete'] is True for x in sources),
         'warning':'Partial or failed cases remain visible; aggregation does not validate any classification.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('inputs',nargs='+',type=pathlib.Path);a=p.parse_args()
 if a.output.exists():p.error('output exists; use a new path')
 result=merge(a.inputs);a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('merged',len(result['results']),'cases')
if __name__=='__main__':main()
