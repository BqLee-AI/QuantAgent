from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Sequence

from alembic import command
from alembic.config import Config

from quantagent.core.config.settings import settings
from quantagent.core.db.session import require_database_url


MIGRATION_ROOT_ENV = "QUANTAGENT_CORE_MIGRATION_ROOT"


def _is_migration_root(path: Path) -> bool:
    return (path / "alembic.ini").is_file() and (path / "alembic").is_dir()


def _iter_candidate_roots(base: Path) -> Sequence[Path]:
    candidates: list[Path] = []
    for candidate in (base, *base.parents):
        candidates.append(candidate)
        candidates.append(candidate / "packages" / "core")
    return candidates


def _migration_root() -> Path:
    configured_root = os.environ.get(MIGRATION_ROOT_ENV)
    if configured_root:
        root = Path(configured_root).expanduser().resolve()
        if _is_migration_root(root):
            return root
        raise FileNotFoundError(
            f"{MIGRATION_ROOT_ENV} must point to a directory containing alembic.ini and alembic/."
        )

    candidates = [
        *_iter_candidate_roots(Path.cwd().resolve()),
        *_iter_candidate_roots(Path(__file__).resolve().parent),
    ]
    for candidate in dict.fromkeys(candidates):
        if _is_migration_root(candidate):
            return candidate

    raise FileNotFoundError(
        "Could not locate QuantAgent core migrations. Run from packages/core "
        f"or set {MIGRATION_ROOT_ENV}."
    )


def create_alembic_config() -> Config:
    package_root = _migration_root()
    config = Config(str(package_root / "alembic.ini"))
    config.set_main_option("script_location", str(package_root / "alembic"))
    return config


@contextmanager
def _database_url_override(database_url: str | None):
    previous_database_url = settings.DATABASE_URL
    previous_env_database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Alembic env.py imports the shared settings singleton in this process,
        # so keep the explicit CLI override on both env and settings paths.
        os.environ["DATABASE_URL"] = database_url
        settings.DATABASE_URL = database_url
    require_database_url(settings.DATABASE_URL)
    try:
        yield
    finally:
        settings.DATABASE_URL = previous_database_url
        if previous_env_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_env_database_url


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantagent-db",
        description="QuantAgent database migration CLI.",
    )
    parser.add_argument(
        "--database-url",
        help="Database URL override. Defaults to DATABASE_URL from the environment or .env.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    upgrade_parser = subparsers.add_parser("upgrade", help="Run Alembic upgrade.")
    upgrade_parser.add_argument("revision", nargs="?", default="head")

    subparsers.add_parser("current", help="Show the current Alembic revision.")
    subparsers.add_parser("check", help="Check whether model metadata matches migrations.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        with _database_url_override(args.database_url):
            config = create_alembic_config()

            if args.command == "upgrade":
                command.upgrade(config, args.revision)
            elif args.command == "current":
                command.current(config)
            elif args.command == "check":
                command.check(config)
            else:  # pragma: no cover - argparse prevents this.
                parser.error(f"unknown command: {args.command}")
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
