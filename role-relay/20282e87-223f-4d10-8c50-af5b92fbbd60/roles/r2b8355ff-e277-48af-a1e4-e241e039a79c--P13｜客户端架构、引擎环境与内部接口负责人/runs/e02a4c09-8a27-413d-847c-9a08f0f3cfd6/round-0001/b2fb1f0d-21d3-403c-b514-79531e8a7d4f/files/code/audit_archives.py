from __future__ import annotations
import csv, hashlib, json, stat, zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work'/'input_audit'
OUT.mkdir(parents=True,exist_ok=True)
queue=[(p,p.name,0) for p in sorted((ROOT/'upload').glob('*.zip'))]
seen={}; archives=[]; members=[]; checks=[]; links=[]
total=0
while queue:
    p,origin,depth=queue.pop(0)
    b=p.read_bytes(); digest=hashlib.sha256(b).hexdigest()
    links.append({'origin':origin,'sha256':digest,'size_bytes':len(b),'depth':depth})
    if digest in seen: continue
    assert depth<=12, 'nesting limit'
    dest=OUT/'extracted'/digest
    seen[digest]=dest
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None, str(p)
        infos=z.infolist(); assert len(infos)<20000
        names=[i.filename for i in infos]; assert len(set(names))==len(names)
        for i in infos:
            n=PurePosixPath(i.filename)
            assert not n.is_absolute() and '..' not in n.parts and '\\' not in i.filename
            assert not stat.S_ISLNK(i.external_attr>>16)
            if i.is_dir(): continue
            assert i.file_size<100_000_000
            total+=i.file_size; assert total<1_000_000_000
            data=z.read(i); target=dest/n
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            h=hashlib.sha256(data).hexdigest()
            members.append({'archive_sha256':digest,'archive_name':p.name,'member_path':str(n),'size_bytes':len(data),'sha256':h,'git_blob_sha1':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'local_path':str(target.relative_to(ROOT))})
            if n.suffix.lower()=='.zip': queue.append((target,origin+'!/'+str(n),depth+1))
        if 'manifest.json' in names:
            m=json.loads(z.read('manifest.json'))
            if m.get('purpose','').startswith('Original relay attachments'):
                for r in m['files']:
                    data=z.read(r['path'])
                    checks.append({'archive_sha256':digest,'path':r['path'],'expected_size':r['size'],'expected_sha256':r['sha256'],'status':'PASS' if len(data)==r['size'] and hashlib.sha256(data).hexdigest()==r['sha256'] else 'FAIL'})
        archives.append({'name':p.name,'sha256':digest,'size_bytes':len(b),'members':sum(not i.is_dir() for i in infos),'uncompressed_bytes':sum(i.file_size for i in infos),'crc_status':'PASS','source_local_path':str(p.relative_to(ROOT)),'extracted_root':str(dest.relative_to(ROOT))})

def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save('archives.json',archives);save('archive_links.json',links);save('members.json',members);save('relay_manifest_checks.json',checks)
summary={'unique_archives':len(archives),'archive_occurrences':len(links),'file_members':len(members),'relay_manifest_records':len(checks),'relay_manifest_pass':sum(x['status']=='PASS' for x in checks),'total_expanded_bytes':total,'scope':'Three supplied uploads and their recursive ZIP members; content hashes deduplicate archives only.'}
save('summary.json',summary)
print(json.dumps(summary,ensure_ascii=False))
for a in archives: print(a['name'],a['sha256'][:12],a['members'])
