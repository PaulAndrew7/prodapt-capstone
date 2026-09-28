"""Local PostgreSQL + pgvector without Docker: `python -m app.cli db-start`, db-stop, db-status.

The pixeltable-pgserver wheel ships PostgreSQL 16 with pgvector for Windows, macOS and Linux,
so `uv sync` installs the database along with the rest of the API. The first start creates a
data directory (LOCAL_DB_DIR, default var/postgres) whose superuser is the user and password in
DATABASE_URL; later starts reuse it. The server listens on localhost at the DATABASE_URL port
and keeps running in the background until `db-stop` or a restart of the computer.
"""

import socket
import subprocess
import sys
import tempfile
from importlib.util import find_spec
from pathlib import Path

from sqlalchemy.engine import URL, make_url

from app.config import get_settings
from app.persistence.db import ensure_database

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
# A UTF-8 aware character type, so full-text search splits words at typographic quotes,
# dashes and non-breaking spaces. With the plain C locale they would be read as letters.
LOCALE = {"win32": "en-US", "darwin": "en_US.UTF-8"}.get(sys.platform, "C.UTF-8")
# Windows: detach the server from this console so Ctrl+C in the terminal does not stop it.
if sys.platform == "win32":
    DETACHED = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
else:
    DETACHED = 0


class LocalDbError(Exception):
    pass


def _bin_dir() -> Path:
    # Located, not imported: importing the package sets up lock files and runtime
    # directories for its own server manager, which is not used here.
    spec = find_spec("pixeltable_pgserver")
    if spec is None or spec.origin is None:
        raise LocalDbError("pixeltable-pgserver is not installed; run `uv sync`")
    return Path(spec.origin).parent / "pginstall" / "bin"


def _target() -> URL:
    url = make_url(get_settings().database_url)
    if url.host not in LOCAL_HOSTS:
        raise LocalDbError(
            f"DATABASE_URL points at {url.host}; db-start only runs a server on localhost"
        )
    if not (url.username and url.password and url.database):
        raise LocalDbError("DATABASE_URL needs a user, password and database name")
    return url


def _data_dir() -> Path:
    return get_settings().local_db_dir.resolve()


def _run(tool: str, *args: str, timeout: float = 90) -> tuple[int, str]:
    # Output goes through a file, not a pipe: the server inherits pg_ctl's handles, and a
    # pipe would stay open for as long as the server runs.
    with tempfile.TemporaryFile("w+", encoding="utf-8", errors="replace") as out:
        done = subprocess.run(  # noqa: S603 - fixed binaries from the installed wheel
            [str(_bin_dir() / tool), *args],
            stdout=out,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            creationflags=DETACHED,
            check=False,
        )
        out.seek(0)
        return done.returncode, out.read().strip()


def _is_running(data: Path) -> bool:
    return (data / "PG_VERSION").exists() and _run("pg_ctl", "status", "-D", str(data))[0] == 0


def _port_in_use(port: int) -> bool:
    try:
        socket.create_connection(("localhost", port), timeout=1).close()
        return True
    except OSError:
        return False


def _init(data: Path, url: URL) -> None:
    data.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pwfile = Path(tmp) / "pw"
        pwfile.write_text(str(url.password), encoding="utf-8")
        code, out = _run(
            "initdb",
            "-D",
            str(data),
            "-U",
            str(url.username),
            f"--pwfile={pwfile}",
            "--auth=scram-sha-256",
            "--encoding=UTF8",
            f"--locale={LOCALE}",
        )
    if code != 0:
        raise LocalDbError(f"initdb failed:\n{out}")


def start() -> str:
    url = _target()
    port = url.port or 5432
    data = _data_dir()
    if _is_running(data):
        ensure_database(url)
        return f"Already running on port {port} (data in {data})"
    if _port_in_use(port):
        raise LocalDbError(
            f"Port {port} is already in use by another program, such as an old Docker "
            "container or another Postgres. Stop it, or change the port in DATABASE_URL."
        )
    created = not (data / "PG_VERSION").exists()
    if created:
        _init(data, url)
    # Outside the data directory: crash recovery reopens every file in it, and Windows
    # keeps the log locked while the server runs.
    log = data.with_name(f"{data.name}.log")
    options = f"-p {port} -h localhost"
    code, out = _run("pg_ctl", "start", "-D", str(data), "-l", str(log), "-w", "-o", options)
    if code != 0:
        tail = "\n".join(log.read_text(errors="replace").splitlines()[-15:]) if log.exists() else ""
        raise LocalDbError(f"The database did not start.\n{out}\n{tail}".strip())
    ensure_database(url)
    action = "Created and started" if created else "Started"
    return f"{action} PostgreSQL on port {port} (data in {data})"


def stop() -> str:
    data = _data_dir()
    if not _is_running(data):
        return "Not running"
    code, out = _run("pg_ctl", "stop", "-D", str(data), "-m", "fast", "-w")
    if code != 0:
        raise LocalDbError(f"pg_ctl stop failed:\n{out}")
    return "Stopped"


def status() -> str:
    data = _data_dir()
    if not (data / "PG_VERSION").exists():
        return f"Not created yet (run db-start; data will be in {data})"
    if _is_running(data):
        return f"Running on port {_target().port or 5432} (data in {data})"
    return f"Stopped (data in {data})"
