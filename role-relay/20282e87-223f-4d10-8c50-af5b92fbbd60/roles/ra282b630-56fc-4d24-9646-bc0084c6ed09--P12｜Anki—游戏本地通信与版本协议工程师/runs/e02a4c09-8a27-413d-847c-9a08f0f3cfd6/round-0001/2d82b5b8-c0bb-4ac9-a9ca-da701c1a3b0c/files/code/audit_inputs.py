from pathlib import Path,PurePosixPath
import zipfile,hashlib,json,stat,csv,io
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'inputs'; OUT.mkdir(exist_ok=True)
H=lambda b:hashlib.sha256(b).hexdigest()
queue=[(p,str(p)) for p in sorted((ROOT.parent/'upload').glob('*.zip'))]
archives={}; aliases=[]; records=[]; validations=[]; errors=[]
while queue:
 p,source=queue.pop(0); raw=p.read_bytes(); sha=H(raw)
 aliases.append({'source':source,'sha256':sha,'size':len(raw)})
 if sha in archives: continue
 folder=OUT/sha[:16]; folder.mkdir(exist_ok=True)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  infos=z.infolist()
  if sum(i.file_size for i in infos)>300_000_000: raise ValueError('archive too large '+source)
  bad=z.testzip()
  if bad: raise ValueError('CRC mismatch '+source+' '+bad)
  members=[]
  for i in infos:
   q=PurePosixPath(i.filename)
   if q.is_absolute() or '..' in q.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16): raise ValueError('unsafe archive path '+i.filename)
   if i.is_dir(): continue
   b=z.read(i); target=folder.joinpath(*q.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
   rec={'archive_sha256':sha,'path':i.filename,'size':len(b),'sha256':H(b),'local_path':str(target.relative_to(ROOT))}
   records.append(rec);members.append(i.filename)
   if i.filename.lower().endswith('.zip'):queue.append((target,sha+'!/'+i.filename))
  for name in members:
   if PurePosixPath(name).name=='manifest.json':
    try:
     obj=json.loads(z.read(name))
    except Exception:continue
    if isinstance(obj,dict) and isinstance(obj.get('files'),list):
     for row in obj['files']:
      if not isinstance(row,dict) or not all(k in row for k in ('path','sha256')):continue
      target=(folder/PurePosixPath(name).parent/row['path']).resolve()
      if not target.is_relative_to(folder.resolve()): raise ValueError('unsafe manifest path')
      size=row.get('size',row.get('size_bytes')); ok=target.is_file() and H(target.read_bytes())==row['sha256'] and (size is None or target.stat().st_size==size)
      r={'kind':'relay_manifest','archive_sha256':sha,'manifest':name,'path':row['path'],'status':'PASS' if ok else 'FAIL'}
      validations.append(r)
      if not ok:errors.append(r)
  archives[sha]={'source':source,'local_dir':str(folder.relative_to(ROOT)),'size':len(raw),'members':len(members),'crc_status':'PASS'}
report={'schema_version':'P12-input-audit/0.1.0','archives':archives,'aliases':aliases,'files':records,'validations':validations,'errors':errors}
(ROOT/'input_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'unique_archives':len(archives),'file_members':len(records),'relay_manifest_checks':len(validations),'errors':errors},ensure_ascii=False,indent=2))
for sha,a in archives.items():print(sha[:16],a['members'],a['source'])
