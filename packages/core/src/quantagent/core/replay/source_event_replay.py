from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import sys
from typing import Sequence
from uuid import uuid4

from sqlalchemy import Select, delete, desc, func, or_, select, text
from sqlalchemy.orm import Session

from quantagent.core.config import settings
from quantagent.core.db.models.event_intake import EventIntakeRoutedEventORM
from quantagent.core.db.models.raw_event import RawEventORM
from quantagent.core.db.models.raw_event_capture import RawEventCaptureORM
from quantagent.core.db.models.scheduler_run import SchedulerRunORM
from quantagent.core.db.session import create_session_factory
from quantagent.core.events import EventEnvelope, EventBusSettings, build_event_bus_runtime
from quantagent.core.events.kafka import AIOKafkaAdminClient
from quantagent.plugin_sdk.io import freeze_json_mapping


DEFAULT_LIMIT = 20
MAX_LIMIT = 500


@dataclass(frozen=True)
class ReplayTarget:
    raw_event: RawEventORM
    capture: RawEventCaptureORM
    run: SchedulerRunORM | None


async def replay_source_events(
    *,
    session: Session,
    raw_event_ids: list[str],
    capture_ids: list[str],
    binding_id: str | None,
    replay_all: bool,
    limit: int,
    clear_routed: bool,
    dry_run: bool,
) -> int:
    targets = _select_targets(
        session=session,
        raw_event_ids=raw_event_ids,
        capture_ids=capture_ids,
        binding_id=binding_id,
        replay_all=replay_all,
        limit=limit,
    )
    if not targets:
        print("No replay targets matched.")
        return 0

    if clear_routed and not dry_run:
        deleted = _clear_routed_rows(session, [item.raw_event.raw_event_id for item in targets])
        session.commit()
        print(f"Cleared routed read-model rows: {deleted}")

    runtime = build_event_bus_runtime(EventBusSettings.from_settings(settings))
    try:
        for target in targets:
            envelope = _build_source_event_envelope(target)
            _print_replay_target(target=target, envelope=envelope, dry_run=dry_run)
            if not dry_run:
                await runtime.publisher.publish(envelope)
        if not dry_run:
            print(f"Replayed source.event.captured messages: {len(targets)}")
        return 0
    finally:
        await runtime.close()


def diagnose_pipeline(session: Session, *, limit: int) -> int:
    print("## runtime config")
    print(f"EVENT_BUS_BACKEND={settings.EVENT_BUS_BACKEND}")
    print(f"EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS={settings.EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS}")
    print(f"EVENT_BUS_KAFKA_DEFAULT_GROUP_ID={settings.EVENT_BUS_KAFKA_DEFAULT_GROUP_ID}")
    print(f"EVENT_BUS_KAFKA_SESSION_TIMEOUT_MS={settings.EVENT_BUS_KAFKA_SESSION_TIMEOUT_MS}")
    print(f"EVENT_BUS_KAFKA_MAX_POLL_INTERVAL_MS={settings.EVENT_BUS_KAFKA_MAX_POLL_INTERVAL_MS}")
    print(f"MODEL_CONFIG_ENCRYPTION_KEY_SET={bool(settings.MODEL_CONFIG_ENCRYPTION_KEY)}")

    print("\n## database counts")
    for label, statement in (
        ("source_bindings", "select status, count(*) from source_bindings group by status order by status"),
        ("scheduler_runs", "select status, count(*) from scheduler_runs group by status order by status"),
        ("raw_events", "select 'total', count(*) from raw_events"),
        ("raw_event_captures", "select 'total', count(*) from raw_event_captures"),
        ("event_intake_routed_events", "select status, count(*) from event_intake_routed_events group by status order by status"),
        ("model_invocations", "select status, count(*) from model_invocations group by status order by status"),
    ):
        print(f"\n### {label}")
        for row in session.execute(text(statement)):
            print(tuple(row))

    print("\n## latest captures without routed row")
    unrouted = _latest_unrouted_captures(session=session, limit=limit)
    for row in unrouted:
        print(
            json.dumps(
                {
                    "raw_event_id": row.raw_event_id,
                    "capture_id": row.capture_id,
                    "binding_id": row.source_binding_id,
                    "scheduler_run_id": row.scheduler_run_id,
                    "captured_at": _iso(row.captured_at),
                    "title": row.title,
                },
                ensure_ascii=False,
            )
        )
    if not unrouted:
        print("none")

    print("\n## latest routed")
    for row in _latest_routed(session=session, limit=limit):
        print(
            json.dumps(
                {
                    "event_id": row.event_id,
                    "raw_event_id": row.raw_event_id,
                    "binding_id": row.binding_id,
                    "decision": row.decision,
                    "status": row.status,
                    "created_at": _iso(row.created_at),
                    "summary": row.summary,
                },
                ensure_ascii=False,
            )
        )

    print("\n## kafka topics / group")
    asyncio.run(_print_kafka_diagnostics())
    return 0


def _select_targets(
    *,
    session: Session,
    raw_event_ids: list[str],
    capture_ids: list[str],
    binding_id: str | None,
    replay_all: bool,
    limit: int,
) -> list[ReplayTarget]:
    if not any((raw_event_ids, capture_ids, binding_id, replay_all)):
        raise ValueError("Provide --raw-event-id, --capture-id, --binding-id, or --all.")
    bounded_limit = _bounded_limit(limit)
    statement: Select[tuple[RawEventORM, RawEventCaptureORM, SchedulerRunORM | None]] = (
        select(RawEventORM, RawEventCaptureORM, SchedulerRunORM)
        .join(RawEventCaptureORM, RawEventCaptureORM.raw_event_id == RawEventORM.raw_event_id)
        .outerjoin(SchedulerRunORM, SchedulerRunORM.run_id == RawEventCaptureORM.scheduler_run_id)
        .order_by(desc(RawEventCaptureORM.captured_at), desc(RawEventCaptureORM.capture_id))
        .limit(bounded_limit)
    )
    predicates = []
    if raw_event_ids:
        predicates.append(RawEventORM.raw_event_id.in_(raw_event_ids))
    if capture_ids:
        predicates.append(RawEventCaptureORM.capture_id.in_(capture_ids))
    if binding_id:
        predicates.append(RawEventCaptureORM.source_binding_id == binding_id)
    if predicates:
        statement = statement.where(or_(*predicates))
    rows = session.execute(statement).all()
    return [ReplayTarget(raw_event=row[0], capture=row[1], run=row[2]) for row in rows]


def _build_source_event_envelope(target: ReplayTarget) -> EventEnvelope:
    request_id = target.capture.request_id or (target.run.request_id if target.run is not None else None) or f"replay-{uuid4().hex}"
    binding_id = target.capture.source_binding_id or target.raw_event.first_binding_id
    if not binding_id:
        raise ValueError(f"raw_event_id={target.raw_event.raw_event_id} has no binding_id for replay.")
    payload = {
        "plugin_id": target.raw_event.source_plugin_id,
        "binding_id": binding_id,
        "items": [_source_item_mapping(target)],
        "next_cursor": None,
        "metadata": {
            "replay": True,
            "replayed_at": datetime.now(UTC).isoformat(),
            "original_capture_id": target.capture.capture_id,
            "original_scheduler_run_id": target.capture.scheduler_run_id,
        },
    }
    return EventEnvelope(
        id=f"evt_replay_{uuid4().hex}",
        topic="source.event.captured",
        payload=freeze_json_mapping(payload, stage="replay"),
        producer="runtime-replay",
        created_at=datetime.now(UTC).isoformat(),
        correlation_id=request_id,
        causation_id=target.capture.scheduler_run_id,
        headers=freeze_json_mapping(
            {
                "request_id": request_id,
                "plugin_id": target.raw_event.source_plugin_id,
                "binding_id": binding_id,
                "item_count": 1,
                "replay": True,
                "raw_event_id": target.raw_event.raw_event_id,
                "capture_id": target.capture.capture_id,
            },
            stage="replay",
        ),
        retry_count=0,
    )


def _source_item_mapping(target: ReplayTarget) -> dict[str, object]:
    metadata = dict(target.raw_event.metadata_json or {})
    metadata.update(dict(target.capture.metadata_json or {}))
    metadata.update(
        {
            "raw_event_id": target.raw_event.raw_event_id,
            "source_event_id": target.raw_event.external_id,
            "capture_id": target.capture.capture_id,
            "source_binding_id": target.capture.source_binding_id,
            "scheduler_run_id": target.capture.scheduler_run_id,
            "request_id": target.capture.request_id,
            "replayed": True,
        }
    )
    return {
        "external_id": target.raw_event.external_id,
        "url": target.raw_event.canonical_url,
        "title": target.raw_event.title,
        "content": target.raw_event.content,
        "author": target.raw_event.author,
        "published_at": _iso(target.raw_event.published_at),
        "captured_at": _iso(target.capture.captured_at),
        "raw_payload": dict(target.raw_event.raw_payload or {}),
        "metadata": metadata,
    }


def _clear_routed_rows(session: Session, raw_event_ids: list[str]) -> int:
    if not raw_event_ids:
        return 0
    result = session.execute(
        delete(EventIntakeRoutedEventORM).where(EventIntakeRoutedEventORM.raw_event_id.in_(raw_event_ids))
    )
    return int(result.rowcount or 0)


def _latest_unrouted_captures(*, session: Session, limit: int):
    statement = text(
        """
        select c.capture_id, c.raw_event_id, c.source_binding_id, c.scheduler_run_id, c.captured_at, r.title
        from raw_event_captures c
        join raw_events r on r.raw_event_id = c.raw_event_id
        left join event_intake_routed_events er on er.raw_event_id = c.raw_event_id
        where er.id is null
        order by c.captured_at desc, c.capture_id desc
        limit :limit
        """
    )
    return session.execute(statement, {"limit": _bounded_limit(limit)}).all()


def _latest_routed(*, session: Session, limit: int) -> list[EventIntakeRoutedEventORM]:
    statement = (
        select(EventIntakeRoutedEventORM)
        .order_by(desc(EventIntakeRoutedEventORM.created_at), desc(EventIntakeRoutedEventORM.id))
        .limit(_bounded_limit(limit))
    )
    return list(session.scalars(statement).all())


async def _print_kafka_diagnostics() -> None:
    if settings.EVENT_BUS_BACKEND != "kafka":
        print("Kafka diagnostics skipped: EVENT_BUS_BACKEND is not kafka.")
        return
    if AIOKafkaAdminClient is None:
        print("Kafka diagnostics skipped: aiokafka admin dependency missing.")
        return
    admin = AIOKafkaAdminClient(
        bootstrap_servers=settings.EVENT_BUS_KAFKA_BOOTSTRAP_SERVERS or "127.0.0.1:19092",
        client_id=f"{settings.EVENT_BUS_KAFKA_CLIENT_ID}-diagnose",
    )
    try:
        await admin.start()
        topics = sorted(await admin.list_topics())
        print("topics=" + ",".join(topic for topic in topics if not topic.startswith("__")))
        print("consumer_group_offsets=unavailable: apache/kafka-native image does not ship kafka-consumer-groups.sh")
    except Exception as exc:
        print(f"kafka diagnostic failed: {exc.__class__.__name__}: {exc}")
    finally:
        await admin.close()


def _print_replay_target(*, target: ReplayTarget, envelope: EventEnvelope, dry_run: bool) -> None:
    print(
        json.dumps(
            {
                "dry_run": dry_run,
                "topic": envelope.topic,
                "message_id": envelope.id,
                "raw_event_id": target.raw_event.raw_event_id,
                "capture_id": target.capture.capture_id,
                "binding_id": envelope.headers.get("binding_id"),
                "title": target.raw_event.title,
            },
            ensure_ascii=False,
        )
    )


def _bounded_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero.")
    return min(limit, MAX_LIMIT)


def _iso(value: object) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()
    return None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantagent-source-event-replay",
        description="Diagnose and replay RawEvent captures back to source.event.captured.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    diagnose = subparsers.add_parser("diagnose", help="Print DB and Kafka pipeline diagnostics.")
    diagnose.add_argument("--limit", type=int, default=10)

    replay = subparsers.add_parser("replay", help="Replay selected RawEvent captures to source.event.captured.")
    replay.add_argument("--raw-event-id", action="append", default=[])
    replay.add_argument("--capture-id", action="append", default=[])
    replay.add_argument("--binding-id")
    replay.add_argument("--all", action="store_true")
    replay.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    replay.add_argument("--clear-routed", action="store_true", help="Delete routed read-model rows for selected raw_event_id before replay.")
    replay.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    session = create_session_factory()()
    try:
        if args.command == "diagnose":
            return diagnose_pipeline(session, limit=args.limit)
        if args.command == "replay":
            return asyncio.run(
                replay_source_events(
                    session=session,
                    raw_event_ids=args.raw_event_id,
                    capture_ids=args.capture_id,
                    binding_id=args.binding_id,
                    replay_all=args.all,
                    limit=args.limit,
                    clear_routed=args.clear_routed,
                    dry_run=args.dry_run,
                )
            )
        parser.error(f"unknown command: {args.command}")
    except Exception as exc:
        print(f"{exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 2
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
