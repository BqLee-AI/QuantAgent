"""repair model config schema drift

Revision ID: 20260603_0001
Revises: 20260601_0005
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260603_0001"
down_revision: str | Sequence[str] | None = "20260601_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PRESET_KEYS = [
    "global_default",
    "economy_text",
    "general_text",
    "reasoning_text",
    "multimodal",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    table_names = set(inspector.get_table_names())
    if "model_invocations" not in table_names:
        raise RuntimeError("Repair migration requires existing model_invocations table.")

    if "model_providers" not in table_names and "model_configs" in table_names:
        _create_model_providers_from_legacy_configs(bind)
        inspector = sa.inspect(bind)
        table_names = set(inspector.get_table_names())

    if "model_providers" not in table_names:
        raise RuntimeError("Repair migration requires model_providers or legacy model_configs table.")

    provider_columns = {column["name"] for column in inspector.get_columns("model_providers")}
    invocation_columns = {column["name"] for column in inspector.get_columns("model_invocations")}

    # 中文注释：部分本地库曾被旧迁移链错误标记到 head，但实际仍停留在单表 model 配置形态。
    # 这里按真实 schema 做幂等修复，而不是再要求开发者手工删库。
    if "model_provider_models" not in table_names:
        op.create_table(
            "model_provider_models",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("provider_id", sa.Integer(), nullable=False),
            sa.Column("model_name", sa.String(length=200), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("supports_vision", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_global_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["provider_id"], ["model_providers.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider_id", "model_name", name="uq_model_provider_models_provider_id_model_name"),
        )

    if "model_preset_bindings" not in table_names:
        op.create_table(
            "model_preset_bindings",
            sa.Column("preset_key", sa.String(length=64), nullable=False),
            sa.Column("primary_model_id", sa.Integer(), nullable=True),
            sa.Column("fallback_model_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["fallback_model_id"], ["model_provider_models.id"]),
            sa.ForeignKeyConstraint(["primary_model_id"], ["model_provider_models.id"]),
            sa.PrimaryKeyConstraint("preset_key"),
        )

    if "provider_id" not in invocation_columns:
        op.add_column("model_invocations", sa.Column("provider_id", sa.Integer(), nullable=True))
    if "preset_key" not in invocation_columns:
        op.add_column("model_invocations", sa.Column("preset_key", sa.String(length=64), nullable=True))

    invocation_foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("model_invocations")}
    if "fk_model_invocations_provider_id" not in invocation_foreign_keys:
        op.create_foreign_key(
            "fk_model_invocations_provider_id",
            "model_invocations",
            "model_providers",
            ["provider_id"],
            ["id"],
        )

    if "model" in provider_columns:
        _backfill_multi_provider_shape(bind)
        op.drop_column("model_providers", "model")
    else:
        _ensure_default_model_rows(bind)

    _ensure_preset_rows(bind)


def downgrade() -> None:
    # 中文注释：repair migration 改的是已经漂移过的库，自动回滚会再次制造 schema/version 不一致。
    raise RuntimeError("20260603_0001 is a forward-only repair migration and cannot be downgraded safely.")


def _create_model_providers_from_legacy_configs(bind: sa.engine.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TABLE model_providers (
                id INTEGER PRIMARY KEY,
                provider_type VARCHAR(64) NOT NULL,
                name VARCHAR(120) NOT NULL,
                base_url VARCHAR(512),
                model VARCHAR(200) NOT NULL,
                enabled BOOLEAN NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT false,
                encrypted_api_key TEXT,
                last_error TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO model_providers
            (id, provider_type, name, base_url, model, enabled, is_default, encrypted_api_key, last_error, created_at, updated_at)
            SELECT id, provider_type, name, base_url, model, enabled, CASE WHEN id = 1 THEN true ELSE false END,
                   encrypted_api_key, last_error, created_at, updated_at
            FROM model_configs
            """
        )
    )


def _backfill_multi_provider_shape(bind: sa.engine.Connection) -> None:
    rows = bind.execute(
        sa.text(
            """
            SELECT id, model, enabled, created_at, updated_at
            FROM model_providers
            ORDER BY is_default DESC, updated_at DESC, id DESC
            """
        )
    ).mappings().all()

    global_default_model_id: int | None = None

    for row in rows:
        model_name = str(row["model"] or "").strip()
        if not model_name:
            continue

        existing_model = bind.execute(
            sa.text(
                """
                SELECT id
                FROM model_provider_models
                WHERE provider_id = :provider_id AND model_name = :model_name
                LIMIT 1
                """
            ),
            {"provider_id": row["id"], "model_name": model_name},
        ).mappings().first()
        if existing_model is not None:
            model_id = existing_model["id"]
        else:
            model_id = bind.execute(
                sa.text(
                    """
                    INSERT INTO model_provider_models
                    (provider_id, model_name, enabled, supports_vision, is_global_default, created_at, updated_at)
                    VALUES
                    (:provider_id, :model_name, :enabled, :supports_vision, :is_global_default, :created_at, :updated_at)
                    RETURNING id
                    """
                ),
                {
                    "provider_id": row["id"],
                    "model_name": model_name,
                    "enabled": row["enabled"],
                    "supports_vision": False,
                    "is_global_default": False,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                },
            ).scalar_one()

        if global_default_model_id is None and row["enabled"]:
            global_default_model_id = model_id
            bind.execute(sa.text("UPDATE model_provider_models SET is_global_default = false"))
            bind.execute(
                sa.text("UPDATE model_provider_models SET is_global_default = true WHERE id = :id"),
                {"id": model_id},
            )

        bind.execute(
            sa.text(
                """
                UPDATE model_invocations
                SET provider_id = COALESCE(provider_id, :provider_id)
                WHERE provider_name = :provider_name
                """
            ),
            {"provider_id": row["id"], "provider_name": _provider_name_for_row(bind, row["id"])},
        )

    if global_default_model_id is not None:
        bind.execute(
            sa.text(
                """
                UPDATE model_preset_bindings
                SET primary_model_id = :model_id
                WHERE preset_key = 'global_default' AND primary_model_id IS NULL
                """
            ),
            {"model_id": global_default_model_id},
        )


def _provider_name_for_row(bind: sa.engine.Connection, provider_id: int) -> str:
    row = bind.execute(
        sa.text("SELECT name FROM model_providers WHERE id = :provider_id"),
        {"provider_id": provider_id},
    ).mappings().first()
    return str(row["name"]) if row is not None else ""


def _ensure_default_model_rows(bind: sa.engine.Connection) -> None:
    provider_rows = bind.execute(
        sa.text(
            """
            SELECT id, name, enabled, created_at, updated_at
            FROM model_providers
            ORDER BY is_default DESC, updated_at DESC, id DESC
            """
        )
    ).mappings().all()

    has_global_default = bind.execute(
        sa.text("SELECT id FROM model_provider_models WHERE is_global_default = true LIMIT 1")
    ).mappings().first()

    for row in provider_rows:
        existing_models = bind.execute(
            sa.text(
                """
                SELECT id
                FROM model_provider_models
                WHERE provider_id = :provider_id
                ORDER BY updated_at DESC, id DESC
                """
            ),
            {"provider_id": row["id"]},
        ).mappings().all()
        if existing_models:
            if has_global_default is None and row["enabled"]:
                bind.execute(sa.text("UPDATE model_provider_models SET is_global_default = false"))
                bind.execute(
                    sa.text("UPDATE model_provider_models SET is_global_default = true WHERE id = :id"),
                    {"id": existing_models[0]["id"]},
                )
                has_global_default = existing_models[0]
            continue

        candidate_model_name = bind.execute(
            sa.text(
                """
                SELECT model
                FROM model_invocations
                WHERE provider_id = :provider_id
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"provider_id": row["id"]},
        ).scalar()
        model_name = str(candidate_model_name or "").strip() or "unknown-model"
        model_id = bind.execute(
            sa.text(
                """
                INSERT INTO model_provider_models
                (provider_id, model_name, enabled, supports_vision, is_global_default, created_at, updated_at)
                VALUES
                (:provider_id, :model_name, :enabled, false, :is_global_default, :created_at, :updated_at)
                RETURNING id
                """
            ),
            {
                "provider_id": row["id"],
                "model_name": model_name,
                "enabled": row["enabled"],
                "is_global_default": has_global_default is None and row["enabled"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            },
        ).scalar_one()
        if has_global_default is None and row["enabled"]:
            has_global_default = {"id": model_id}


def _ensure_preset_rows(bind: sa.engine.Connection) -> None:
    global_default_model_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM model_provider_models
            WHERE is_global_default = true
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """
        )
    ).scalar()

    for preset_key in PRESET_KEYS:
        existing = bind.execute(
            sa.text("SELECT preset_key FROM model_preset_bindings WHERE preset_key = :preset_key LIMIT 1"),
            {"preset_key": preset_key},
        ).mappings().first()
        if existing is None:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO model_preset_bindings (preset_key, primary_model_id, fallback_model_id, updated_at)
                    VALUES (:preset_key, :primary_model_id, NULL, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "preset_key": preset_key,
                    "primary_model_id": global_default_model_id if preset_key == "global_default" else None,
                },
            )
        elif preset_key == "global_default" and global_default_model_id is not None:
            bind.execute(
                sa.text(
                    """
                    UPDATE model_preset_bindings
                    SET primary_model_id = COALESCE(primary_model_id, :primary_model_id)
                    WHERE preset_key = :preset_key
                    """
                ),
                {"preset_key": preset_key, "primary_model_id": global_default_model_id},
            )
