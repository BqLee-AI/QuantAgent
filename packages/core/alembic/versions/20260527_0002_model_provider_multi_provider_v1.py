"""model provider multi provider v1

Revision ID: 20260527_0002
Revises: 20260526_0001
Create Date: 2026-05-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_0002"
down_revision = "20260526_0001"
branch_labels = None
depends_on = None


PRESET_KEYS = [
    "global_default",
    "economy_text",
    "general_text",
    "reasoning_text",
    "multimodal",
]


def upgrade() -> None:
    op.create_table(
        "model_providers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
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
    op.add_column("model_invocations", sa.Column("provider_id", sa.Integer(), nullable=True))
    op.add_column("model_invocations", sa.Column("preset_key", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_model_invocations_provider_id",
        "model_invocations",
        "model_providers",
        ["provider_id"],
        ["id"],
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT id, provider_type, name, base_url, model, enabled, encrypted_api_key, last_error, created_at, updated_at
            FROM model_configs
            """
        )
    ).mappings().all()
    global_default_model_id: int | None = None
    if rows:
        legacy = rows[0]
        provider_id = connection.execute(
            sa.text(
                """
                INSERT INTO model_providers
                (provider_type, name, base_url, enabled, is_default, encrypted_api_key, last_error, created_at, updated_at)
                VALUES
                (:provider_type, :name, :base_url, :enabled, :is_default, :encrypted_api_key, :last_error, :created_at, :updated_at)
                """
            ),
            {
                "provider_type": legacy["provider_type"],
                "name": legacy["name"],
                "base_url": legacy["base_url"],
                "enabled": legacy["enabled"],
                "is_default": True,
                "encrypted_api_key": legacy["encrypted_api_key"],
                "last_error": legacy["last_error"],
                "created_at": legacy["created_at"],
                "updated_at": legacy["updated_at"],
            },
        ).lastrowid

        if provider_id is not None and legacy["model"]:
            global_default_model_id = connection.execute(
                sa.text(
                    """
                    INSERT INTO model_provider_models
                    (provider_id, model_name, enabled, supports_vision, is_global_default, created_at, updated_at)
                    VALUES
                    (:provider_id, :model_name, :enabled, :supports_vision, :is_global_default, :created_at, :updated_at)
                    """
                ),
                {
                    "provider_id": provider_id,
                    "model_name": legacy["model"],
                    "enabled": legacy["enabled"],
                    "supports_vision": False,
                    "is_global_default": True,
                    "created_at": legacy["created_at"],
                    "updated_at": legacy["updated_at"],
                },
            ).lastrowid

        if provider_id is not None:
            connection.execute(sa.text("UPDATE model_invocations SET provider_id = :provider_id"), {"provider_id": provider_id})

    for preset_key in PRESET_KEYS:
        connection.execute(
            sa.text(
                """
                INSERT INTO model_preset_bindings (preset_key, primary_model_id, fallback_model_id, updated_at)
                VALUES (:preset_key, :primary_model_id, :fallback_model_id, CURRENT_TIMESTAMP)
                """
            ),
            {
                "preset_key": preset_key,
                "primary_model_id": global_default_model_id if preset_key == "global_default" else None,
                "fallback_model_id": None,
            },
        )

    op.drop_table("model_configs")


def downgrade() -> None:
    op.create_table(
        "model_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    connection = op.get_bind()
    default_provider = connection.execute(
        sa.text(
            """
            SELECT provider_type, name, base_url, enabled, encrypted_api_key, last_error, created_at, updated_at, id
            FROM model_providers
            ORDER BY is_default DESC, updated_at DESC, id DESC
            LIMIT 1
            """
        )
    ).mappings().first()
    if default_provider:
        default_model = connection.execute(
            sa.text(
                """
                SELECT model_name
                FROM model_provider_models
                WHERE provider_id = :provider_id
                ORDER BY is_global_default DESC, updated_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"provider_id": default_provider["id"]},
        ).mappings().first()
        connection.execute(
            sa.text(
                """
                INSERT INTO model_configs
                (id, provider_type, name, base_url, model, enabled, encrypted_api_key, last_error, created_at, updated_at)
                VALUES
                (1, :provider_type, :name, :base_url, :model, :enabled, :encrypted_api_key, :last_error, :created_at, :updated_at)
                """
            ),
            {
                "provider_type": default_provider["provider_type"],
                "name": default_provider["name"],
                "base_url": default_provider["base_url"],
                "model": default_model["model_name"] if default_model else "",
                "enabled": default_provider["enabled"],
                "encrypted_api_key": default_provider["encrypted_api_key"],
                "last_error": default_provider["last_error"],
                "created_at": default_provider["created_at"],
                "updated_at": default_provider["updated_at"],
            },
        )

    op.drop_constraint("fk_model_invocations_provider_id", "model_invocations", type_="foreignkey")
    op.drop_column("model_invocations", "preset_key")
    op.drop_column("model_invocations", "provider_id")
    op.drop_table("model_preset_bindings")
    op.drop_table("model_provider_models")
    op.drop_table("model_providers")
