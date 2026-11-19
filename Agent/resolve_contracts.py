#!/usr/bin/env python3
"""Conservatively resolve JDK documentation into attributed source passages."""
import argparse, hashlib, json, pathlib, re

# Explicit review leads, not a claim that all applicable contracts are covered.
RELATED = {
 'java.util.Hashtable.keys()': ['java.util.Enumeration'],
 'java.util.stream.Collectors.<T>toList()': ['java.util.stream.Collector', 'java.util.stream.Stream', 'java.util.List'],
 'java.util.stream.Stream.findFirst()': ['java.util.stream.Stream'],
 'java.util.Arrays.<T>asList(T...)': ['java.util.List'],
 'java.util.Collections.<T>singletonList(T)': ['java.util.List'],
}

def load_jsonl(path):
 with path.open() as f: return [json.loads(x) for x in f if x.strip()]

def passage(owner, kind, doc, source, declaration):
 value={'owner':owner,'kind':kind,'source':source,'declaration':declaration,'text':doc}
 value['id']=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()[:20]
 return value

def split_types(text):
 if not text.strip(): return []
 parts=[]; start=0; depth=0
 for i,c in enumerate(text):
  if c=='<': depth+=1
  elif c=='>':
   depth-=1
   if depth<0:return None
  elif c==',' and depth==0:parts.append(text[start:i].strip());start=i+1
 if depth:return None
 parts.append(text[start:].strip())
 return parts

def signature_parts(signature, declaration=False):
 # Exact text only: no package-name guessing, erasure, annotation removal or inferred types.
 match=re.search(r'([A-Za-z_$][\w$]*)\((.*)\)\s*$',signature or '')
 if not match:return None
 params=split_types(match.group(2))
 if params is None:return None
 if declaration:
  types=[]
  for param in params:
   m=re.fullmatch(r'(.+?)\s+[A-Za-z_$][\w$]*',param)
   if not m:return None
   types.append(m.group(1))
  params=types
 return match.group(1),tuple(re.sub(r'\s+','',x) for x in params)

def resolve(record, docs, source_hash, docs_integrity='unverified'):
 owner=record.get('owner'); sig=record.get('signature'); ctx=record.get('contract_context') or {}
 name=str(owner)+'.'+str(sig); methods=ctx.get('matching_method_name_overloads') or []
 result={'api_id':record['id'],'owner':owner,'signature':sig,'kind':record.get('kind'),
         'jdk_source_sha256':source_hash,'docs_artifact_integrity':docs_integrity,'resolution':'unresolved','passages':[], 'unresolved':[],
         'sample_sites':record.get('sample_sites',[]),'call_count':record.get('call_count',0)}
 if not owner or not sig:
  result['unresolved'].append('Compiler did not resolve an owner and signature.'); return result
 canonical=docs.get(owner)
 if not canonical:
  result['unresolved'].append('Declaring class is absent from the JDK documentation artifact.');return result
 if docs_integrity!='verified':result['unresolved'].append('JDK documentation artifact hash not recorded; source artifact integrity is unverified.')
 cls=canonical.get('class') or {}; docloc={'module':canonical.get('module'),'source_entry':canonical.get('source_entry')}
 target_name=signature_parts(sig)
 methods=(canonical.get('methods') or {}).get(target_name[0],[]) if target_name else []
 if cls.get('doc'):result['passages'].append(passage(owner,'declaring_class',cls['doc'],docloc,cls.get('declaration')))
 # Conservative source-text matching; equivalent but differently written types remain unresolved.
 target=signature_parts(sig)
 selected=[item for item in methods if target is not None and signature_parts(item.get('declaration'),True)==target]
 if len(selected)==1 and selected[0].get('doc'):
  result['resolution']='source_signature_match'
  result['passages'].append(passage(owner,'matched_method',selected[0]['doc'],docloc,selected[0].get('declaration')))
 else:
  result['unresolved'].append('Exact source overload not resolved or method Javadoc missing; no method contract selected.')
 for related in RELATED.get(name,[]):
  entry=docs.get(related)
  if not entry or not (entry.get('class') or {}).get('doc'):
   result['unresolved'].append('Related class documentation unavailable: '+related);continue
  cl=entry['class']; loc={'module':entry.get('module'),'source_entry':entry.get('source_entry')}
  result['passages'].append(passage(related,'related_class',cl['doc'],loc,cl.get('declaration')))
 result['unresolved'] += ['Inherited members and linked contracts are not fully resolved.',
  'Concrete receiver, source-level applicability, dependency versions and runtime dispatch remain unverified.',
  'Related classes are review leads, not a complete contract closure.']
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',type=pathlib.Path,required=True);p.add_argument('--docs',type=pathlib.Path,required=True);p.add_argument('--coverage',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--select',action='append',default=[]);a=p.parse_args()
 coverage=json.loads(a.coverage.read_text());digest=coverage['jdk_source_sha256']
 expected_docs=coverage.get('jdk_docs_sha256');actual_docs=hashlib.sha256(a.docs.read_bytes()).hexdigest()
 if expected_docs and expected_docs!=actual_docs:raise ValueError('JDK documentation artifact hash mismatch')
 docs_integrity='verified' if expected_docs else 'unverified'
 docs={x['owner']:x for x in load_jsonl(a.docs)}; rows=load_jsonl(a.queue)
 if a.select:rows=[r for r in rows if any(s in str(r.get('owner'))+'.'+str(r.get('signature')) for s in a.select)]
 for row in rows:
  expected=hashlib.sha256(json.dumps([digest,row.get('owner'),row.get('signature'),row.get('kind')]).encode()).hexdigest()[:20]
  if row.get('id')!=expected:raise ValueError('queue ID does not match the JDK source digest and signature')
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('w') as f:
  for row in rows:f.write(json.dumps(resolve(row,docs,digest,docs_integrity),ensure_ascii=False)+'\n')
 print(json.dumps({'groups':len(rows),'output':str(a.output)}))
if __name__=='__main__':main()
