"""Betriebsbefehle.

    python -m app.cli migrate                     Migrationen ausführen
    python -m app.cli create-admin --email ...    Erstadministrator anlegen (Passwort interaktiv)
    python -m app.cli seed                        Beispieldaten laden (idempotent)
    python -m app.cli backup [--kind manual]      Sicherung erstellen
    python -m app.cli list-backups                Sicherungen auflisten
    python -m app.cli verify-backup DATEI         Sicherung prüfen
    python -m app.cli restore DATEI               Sicherung wiederherstellen (Anwendung gestoppt)
    python -m app.cli serve                       Server starten
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy import select

from .config import settings


def cmd_migrate(_args) -> int:
    from .migrations import upgrade_head

    upgrade_head()
    print("Migrationen ausgeführt.")
    return 0


def cmd_create_admin(args) -> int:
    from .audit import audit
    from .db import db_session
    from .migrations import upgrade_head
    from .models import ROLE_ADMIN, User
    from .security import hash_password, normalize_email, password_problem

    upgrade_head()
    email = normalize_email(args.email)
    if "@" not in email:
        print("Ungültige E-Mail-Adresse.", file=sys.stderr)
        return 2
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass("Passwort für den Administrator: ")
        repeat = getpass.getpass("Passwort wiederholen: ")
        if password != repeat:
            print("Die Passwörter stimmen nicht überein.", file=sys.stderr)
            return 2
    problem = password_problem(password)
    if problem:
        print(f"Passwort ungeeignet: {problem}", file=sys.stderr)
        return 2
    with db_session() as db:
        if db.scalar(select(User).where(User.email == email)):
            print("Ein Benutzer mit dieser E-Mail existiert bereits.", file=sys.stderr)
            return 1
        user = User(email=email, display_name=args.name or email.split("@")[0], role=ROLE_ADMIN, password_hash=hash_password(password))
        db.add(user)
        db.flush()
        audit(db, None, "admin_created_cli", "user", user.id)
        db.commit()
    print(f"Administrator {email} angelegt.")
    return 0


def cmd_seed(_args) -> int:
    from .db import db_session
    from .migrations import upgrade_head
    from .seed.loader import load_seed

    upgrade_head()
    with db_session() as db:
        created = load_seed(db)
    print("Beispieldaten geladen:", json.dumps(created, ensure_ascii=False))
    return 0


def cmd_backup(args) -> int:
    from .services.backup import BackupError, create_backup, prune_backups

    try:
        target = Path(args.output) if args.output else None
        path = create_backup(args.kind, target)
    except BackupError as exc:
        print(f"Sicherung fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    if args.kind == "daily":
        prune_backups("daily")
    print(path)
    return 0


def cmd_list_backups(_args) -> int:
    for p in sorted(settings.backup_dir.glob("lehrplan-*.tar.gz")):
        print(f"{p.name}\t{p.stat().st_size} Bytes")
    return 0


def cmd_verify_backup(args) -> int:
    from .services.backup import BackupError, verify_backup

    with tempfile.TemporaryDirectory() as tmp:
        try:
            manifest = verify_backup(_resolve_backup(args.file), Path(tmp))
        except BackupError as exc:
            print(f"Sicherung ungültig: {exc}", file=sys.stderr)
            return 1
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"} | {"files": len(manifest["files"])}, indent=2, ensure_ascii=False))
    return 0


def _resolve_backup(name: str) -> Path:
    p = Path(name)
    if not p.exists() and (settings.backup_dir / name).exists():
        p = settings.backup_dir / name
    return p


def cmd_restore(args) -> int:
    from .services.backup import BackupError, restore_backup

    try:
        result = restore_backup(_resolve_backup(args.file), force=args.force, pre_backup=not args.no_pre_backup)
    except BackupError as exc:
        print(f"Wiederherstellung abgebrochen: {exc}", file=sys.stderr)
        return 1
    m = result["manifest"]
    print(f"Wiederhergestellt: Stand {m['created_at']} (Software {m['software_version']}, Schema {m['schema_version']}).")
    if result["pre_restore_backup"]:
        print(f"Vorheriger Stand gesichert: {result['pre_restore_backup']}")
    # Neuere Software: Schema ggf. anheben
    from .migrations import upgrade_head

    upgrade_head()
    return 0


def cmd_serve(args) -> int:
    import uvicorn

    from .migrations import upgrade_head

    upgrade_head()
    kwargs = {}
    if settings.tls_cert_file and settings.tls_key_file:
        kwargs = {"ssl_certfile": settings.tls_cert_file, "ssl_keyfile": settings.tls_key_file}
    uvicorn.run("app.main:app", host=args.host, port=args.port, workers=args.workers, proxy_headers=False, **kwargs)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Unterrichtsassistent – Betriebsbefehle")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate").set_defaults(fn=cmd_migrate)
    p = sub.add_parser("create-admin")
    p.add_argument("--email", required=True)
    p.add_argument("--name")
    p.add_argument("--password-stdin", action="store_true", help="Passwort aus erster Zeile von stdin lesen")
    p.set_defaults(fn=cmd_create_admin)
    sub.add_parser("seed").set_defaults(fn=cmd_seed)
    p = sub.add_parser("backup")
    p.add_argument("--kind", default="manual", choices=["manual", "daily", "export"])
    p.add_argument("--output", help="Zielverzeichnis (Standard: DATA_DIR/backups)")
    p.set_defaults(fn=cmd_backup)
    sub.add_parser("list-backups").set_defaults(fn=cmd_list_backups)
    p = sub.add_parser("verify-backup")
    p.add_argument("file")
    p.set_defaults(fn=cmd_verify_backup)
    p = sub.add_parser("restore")
    p.add_argument("file")
    p.add_argument("--force", action="store_true", help="Laufzeitprüfung überspringen (nur wenn sicher gestoppt)")
    p.add_argument("--no-pre-backup", action="store_true")
    p.set_defaults(fn=cmd_restore)
    p = sub.add_parser("serve")
    p.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    p.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", "2")), help="Anzahl Worker-Prozesse (Standard 2)")
    p.set_defaults(fn=cmd_serve)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
