"""Resolve only isolated P13 output paths; never authorizes a real repository."""
from pathlib import Path, PurePosixPath


def isolated_output_path(root: Path, relative: str) -> Path:
    if type(relative) is not str or not relative or '\\' in relative or ':' in relative:
        raise ValueError('INVALID_RELATIVE_PATH')
    rel=PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or '.' in relative.split('/') or '' in relative.split('/'):
        raise ValueError('PATH_TRAVERSAL')
    allowed=(relative.startswith('architecture/') or relative.startswith('contracts/internal/') or
             relative.startswith('runtime/framework/') or relative in {'README.md','delivery_manifest.sha256.tsv'})
    if not allowed or relative=='architecture/evidence/upstream' or relative.startswith('architecture/evidence/upstream/'):
        raise ValueError('PATH_OUTSIDE_P13_WRITE_SCOPE')
    root=root.resolve(); path=root.joinpath(*rel.parts)
    current=root
    for part in rel.parts:
        current=current/part
        if current.is_symlink():
            raise ValueError('SYMLINK_NOT_ALLOWED')
    if not path.resolve().is_relative_to(root):
        raise ValueError('PATH_ESCAPES_PACKAGE')
    return path

