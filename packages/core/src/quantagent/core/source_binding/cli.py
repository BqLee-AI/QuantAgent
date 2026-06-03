from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quantagent.core.db.session import create_session_factory
from quantagent.core.registry import PluginRegistry, RegistryScanner
from quantagent.core.db.repositories.source_binding_repository import SourceBindingRepository
from quantagent.core.source_binding.installer import (
    SemiconductorSourceBindingInstaller,
    SemiconductorSourceBindingInstallOptions,
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "install-semiconductor-defaults":
        return _install_semiconductor_defaults(args)
    parser.print_help(sys.stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantagent-source-bindings")
    subparsers = parser.add_subparsers(dest="command")
    install = subparsers.add_parser(
        "install-semiconductor-defaults",
        help="从官方半导体行业包模板安装默认 RSS SourceBinding。",
    )
    install.add_argument("--no-expansion", action="store_true", help="只安装 baseline RSS binding。")
    install.add_argument("--pause-expansion", action="store_true", help="安装 expansion 但保持 paused。")
    install.add_argument("--no-force-due", action="store_true", help="不把安装后的 active binding 立即设为 due。")
    install.add_argument("--baseline-interval-seconds", type=int, default=300)
    install.add_argument("--expansion-interval-seconds", type=int, default=900)
    install.add_argument("--max-items-per-feed", type=int, default=20)
    install.add_argument("--official-plugins-root", type=Path, default=None)
    install.add_argument("--runtime-plugins-root", type=Path, default=None)
    return parser


def _install_semiconductor_defaults(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    official_root = args.official_plugins_root or repo_root / "plugins"
    runtime_root = args.runtime_plugins_root or repo_root / "runtime" / "plugins"
    session_factory = create_session_factory()
    session = session_factory()
    try:
        registry = PluginRegistry(RegistryScanner(official_root=official_root, runtime_root=runtime_root))
        installer = SemiconductorSourceBindingInstaller(
            registry=registry,
            repository=SourceBindingRepository(session),
        )
        result = installer.install_defaults(
            SemiconductorSourceBindingInstallOptions(
                include_expansion=not args.no_expansion,
                activate_expansion=not args.pause_expansion,
                force_due=not args.no_force_due,
                baseline_interval_seconds=args.baseline_interval_seconds,
                expansion_interval_seconds=args.expansion_interval_seconds,
                max_items_per_feed=args.max_items_per_feed,
            )
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        print(f"failed to install semiconductor source bindings: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()

    for item in result.installed:
        due = item.next_run_at.isoformat() if item.next_run_at is not None else "not-due"
        print(
            f"{item.action} {item.binding_id} tier={item.source_tier} "
            f"feeds={item.feed_count} interval_seconds={item.interval_seconds} next_run_at={due}"
        )
    return 0


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "plugins").is_dir():
            return parent
    return Path.cwd()


if __name__ == "__main__":
    raise SystemExit(main())
