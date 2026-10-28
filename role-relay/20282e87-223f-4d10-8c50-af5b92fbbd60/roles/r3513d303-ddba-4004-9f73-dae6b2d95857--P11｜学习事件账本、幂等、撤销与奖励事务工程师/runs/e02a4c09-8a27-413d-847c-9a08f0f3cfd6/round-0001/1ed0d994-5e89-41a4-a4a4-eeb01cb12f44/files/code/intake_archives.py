"""Read all supplied ZIP bytes, safely extract each distinct archive, verify relay manifests."""
import hashlib, json, pathlib, stat, zipfile

BASE = pathlib.Path(__file__).resolve().parent
DEST = BASE / 'intake'
DEST.mkdir(exist_ok=True)
seen, archives, members, manifest_checks = {}, [], [], []
queue = list(sorted((BASE / 'upload').glob('*.zip')))
while queue:
    path = queue.pop(0)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha in seen:
        continue
    dest = DEST / sha
    dest.mkdir(exist_ok=True)
    seen[sha] = str(dest)
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if len(entries) > 30000 or sum(i.file_size for i in entries) > 400_000_000:
            raise ValueError('archive limits: ' + str(path))
        names = set()
        for info in entries:
            pure = pathlib.PurePosixPath(info.filename)
            if pure.is_absolute() or '..' in pure.parts or '\\' in info.filename or str(pure) in names:
                raise ValueError('unsafe or duplicate member: ' + info.filename)
            names.add(str(pure))
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('symlink: ' + info.filename)
            out = dest.joinpath(*pure.parts)
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            data = z.read(info)  # includes per-member CRC validation
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            item = {'archive_sha256':sha,'member':info.filename,'size_bytes':len(data),
                    'sha256':hashlib.sha256(data).hexdigest(),'local_path':str(out.relative_to(BASE))}
            members.append(item)
            if info.filename.lower().endswith('.zip'):
                queue.append(out)
        checks = 0
        if 'manifest.json' in z.namelist():
            manifest = json.loads(z.read('manifest.json'))
            if manifest.get('purpose','').startswith('Original relay attachments'):
                for r in manifest['files']:
                    b = z.read(r['path'])
                    ok = len(b) == r['size'] and hashlib.sha256(b).hexdigest() == r['sha256']
                    manifest_checks.append({'archive_sha256':sha,'path':r['path'],'status':'PASS' if ok else 'FAIL'})
                    if not ok: raise ValueError('manifest mismatch')
                    checks += 1
        archives.append({'input_path':str(path.relative_to(BASE)),'sha256':sha,'size_bytes':path.stat().st_size,
                         'member_count':len(entries),'crc_status':'PASS','relay_manifest_entries_verified':checks})
report = {'schema_version':'P11-INTAKE/0.1.0','archives':archives,'members':members,'relay_manifest_checks':manifest_checks}
(DEST / 'intake_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'distinct_archives':len(archives),'file_members':len(members),'relay_manifest_checks':len(manifest_checks),
                  'status':'PASS','report':str(DEST/'intake_report.json')},ensure_ascii=False))
