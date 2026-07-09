import os
import ntpath
import posixpath
import shutil
import uuid


def is_valid_directory_path(path: str, validate_writability: bool = True) -> bool:
    if not (posixpath.isabs(path) or ntpath.isabs(path)):
        return False

    if "\0" in path:
        return False

    if not validate_writability:
        if os.name == "nt" and ntpath.isabs(path):
            drive, _ = ntpath.splitdrive(path)
            root = f"{drive}\\" if drive else "\\"
            return os.path.exists(root)

        return True

    try:
        probe = os.path.join(path, f".saberr_write_probe_{uuid.uuid4().hex}")
        fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        return False
    os.close(fd)
    try:
        os.remove(probe)
    except OSError:
        pass
    return True


def get_disk_for_path(path: str) -> tuple[str, int | None, int | None]:
    # returns (mount_point, total_bytes, used_bytes)
    mount = os.path.realpath(path)
    while not os.path.ismount(mount):
        parent = os.path.dirname(mount)
        if parent == mount:
            break
        mount = parent
    try:
        usage = shutil.disk_usage(path)
        return mount, usage.total, usage.used
    except OSError:
        return mount, None, None


def get_local_path_from_remote(remote_path: str, mapping: tuple[str, str] | None) -> str:
    if not mapping:
        return remote_path
    remote, local = mapping

    remote_is_windows = ntpath.isabs(remote) and not posixpath.isabs(remote)
    remote_mod = ntpath if remote_is_windows else posixpath
    norm_path = remote_mod.normpath(remote_path)
    norm_remote = remote_mod.normpath(remote)

    cmp_path = norm_path.lower() if remote_is_windows else norm_path
    cmp_remote = norm_remote.lower() if remote_is_windows else norm_remote

    if cmp_path == cmp_remote:
        remainder = ""
    elif cmp_path.startswith(cmp_remote + remote_mod.sep):
        remainder = norm_path[len(norm_remote):].lstrip("\\/")
    else:
        return remote_path

    local_is_windows = ntpath.isabs(local) and not posixpath.isabs(local)
    local_mod = ntpath if local_is_windows else posixpath
    if not remainder:
        return local_mod.normpath(local)
    return local_mod.normpath(local_mod.join(local, *remainder.replace("\\", "/").split("/")))
