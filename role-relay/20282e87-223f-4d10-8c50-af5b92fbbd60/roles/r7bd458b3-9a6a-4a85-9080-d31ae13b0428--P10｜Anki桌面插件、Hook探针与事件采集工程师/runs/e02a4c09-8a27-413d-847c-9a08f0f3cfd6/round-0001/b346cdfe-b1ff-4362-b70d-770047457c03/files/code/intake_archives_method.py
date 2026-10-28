from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "intake"
OUT.mkdir(parents=True, exist_ok=True)
report = {"status": "PASS", "outer_archives": [], "archives": [], "relay_checks": [], "members": [], "errors": []}
seen = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def visit(data, chain, depth=0):
    digest = sha(data)
    if digest in seen:
        seen[digest]["additional_chains"].append(chain)
        return
    if depth > 12:
        raise ValueError("Archive nesting exceeds inspection budget")
    directory = OUT / ("zip_" + digest[:16])
    directory.mkdir(exist_ok=True)
    entry = {"sha256": digest, "size_bytes": len(data), "chain": chain, "additional_chains": [], "local_dir": str(directory.relative_to(ROOT)), "files": 0}
    seen[digest] = entry
    report["archives"].append(entry)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if sum(i.file_size for i in archive.infolist()) > 300_000_000:
            raise ValueError("Archive expansion exceeds inspection budget")
        names = set()
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or stat.S_ISLNK(info.external_attr >> 16) or name in names:
                raise ValueError("Unsafe/duplicate archive member: " + name)
            names.add(name)
            if info.is_dir():
                continue
            content = archive.read(info)  # Also validates CRC for every member.
            target = directory.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            report["members"].append({"archive_sha256": digest, "member": name, "size_bytes": len(content), "sha256": sha(content), "local_path": str(target.relative_to(ROOT))})
            entry["files"] += 1
        entry["crc"] = "PASS"
        if "manifest.json" in names:
            manifest = json.loads(archive.read("manifest.json"))
            if isinstance(manifest, dict) and isinstance(manifest.get("files"), list):
                for expected in manifest["files"]:
                    if not all(key in expected for key in ("path", "size", "sha256")):
                        continue
                    content = archive.read(expected["path"])
                    valid = len(content) == expected["size"] and sha(content) == expected["sha256"]
                    report["relay_checks"].append({"archive_sha256": digest, "member": expected["path"], "status": "PASS" if valid else "FAIL"})
                    if not valid:
                        report["errors"].append({"archive": digest, "member": expected["path"], "error": "manifest mismatch"})
        for info in archive.infolist():
            if not info.is_dir() and info.filename.lower().endswith(".zip"):
                visit(archive.read(info), chain + [info.filename], depth + 1)


for file in sorted((ROOT.parent / "upload").glob("*.zip")):
    content = file.read_bytes()
    report["outer_archives"].append({"path": file.name, "size_bytes": len(content), "sha256": sha(content)})
    visit(content, [file.name])
report["status"] = "FAIL" if report["errors"] else "PASS"
report["summary"] = {"unique_zip_count": len(report["archives"]), "extracted_member_count": len(report["members"]), "relay_manifest_checks": len(report["relay_checks"]), "errors": len(report["errors"])}
(ROOT / "intake_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False))
for archive in report["archives"]:
    print(json.dumps(archive, ensure_ascii=False))
