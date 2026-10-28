"""POSIX isolation helpers. Windows DACL provisioning awaits P34/P38 testing."""
from pathlib import Path
import os
import secrets
import stat


def private_directory(path, *, create=False):
    path = Path(path).absolute()
    if os.name != 'posix':
        raise OSError('WINDOWS_DACL_GATE_NOT_IMPLEMENTED')
    if create and not path.exists():
        path.mkdir(mode=0o700)
    s = path.lstat()
    if (not stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode) or
            s.st_uid != os.getuid() or stat.S_IMODE(s.st_mode) & 0o077):
        raise PermissionError('OWNED_PRIVATE_DIRECTORY_REQUIRED')
    return path


def create_key(directory, name='pairing.key'):
    directory = private_directory(directory)
    if name != 'pairing.key':
        raise ValueError('FIXED_KEY_NAME_REQUIRED')
    path = directory / name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, 0o600)
    secret = secrets.token_bytes(32)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(secret); stream.flush(); os.fsync(stream.fileno())
        dfd = os.open(directory, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except BaseException:
        # Do not silently replace an uncertain pairing file on retry.
        raise
    return path


def read_key(directory):
    directory = private_directory(directory)
    path = directory / 'pairing.key'
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        s = os.fstat(stream.fileno())
        if (not stat.S_ISREG(s.st_mode) or s.st_uid != os.getuid() or
                stat.S_IMODE(s.st_mode) & 0o077 or s.st_nlink != 1 or s.st_size != 32):
            raise PermissionError('PRIVATE_PAIRING_KEY_REQUIRED')
        return stream.read(33)
