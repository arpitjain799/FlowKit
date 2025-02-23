# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Initial migration

Revision ID: 66dee292d147
Revises: 
Create Date: 2023-01-23 10:16:16.536867

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import Integer


# revision identifiers, used by Alembic.
revision = "66dee292d147"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=75), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=True),
        sa.Column("latest_token_expiry", sa.DateTime(), nullable=False),
        sa.Column("longest_token_life_minutes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["server.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "server_id"),
    )
    op.create_table(
        "scope",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("server_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["server.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "server_id"),
    )
    op.create_table(
        "token_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=75), nullable=False),
        sa.Column("_token", sa.Text(), nullable=False),
        sa.Column("expiry", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["server.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scopes_in_role",
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
        ),
        sa.ForeignKeyConstraint(
            ["scope_id"],
            ["scope.id"],
        ),
        sa.PrimaryKeyConstraint("scope_id", "role_id"),
    )
    op.create_table(
        "users_with_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["role.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.drop_table("group_server_permission")
    op.drop_table("server_capability")
    op.drop_table("group_server_token_limits")
    op.drop_table("group_memberships")
    op.drop_table("group")
    op.drop_table("token")
    op.alter_column(
        "server",
        column_name="longest_token_life",
        new_column_name="longest_token_life_minutes",
        type_=Integer,
        existing_type=Integer,
    )

    # ### end Alembic commands ###


def downgrade():
    # ### Downgrade is untested! Use with caution! ###
    op.alter_column(
        "server",
        column_name="longest_token_life_minutes",
        new_column_name="longest_token_life",
    )

    op.create_table(
        "token",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=75), nullable=False),
        sa.Column("_token", sa.TEXT(), nullable=False),
        sa.Column("expires", sa.DATETIME(), nullable=False),
        sa.Column("owner_id", sa.INTEGER(), nullable=False),
        sa.Column("server_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["server.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "group_server_permission",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("group_id", sa.INTEGER(), nullable=False),
        sa.Column("server_capability_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["group.id"],
        ),
        sa.ForeignKeyConstraint(
            ["server_capability_id"],
            ["server_capability.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id", "server_capability_id", name="_group_servercap_uc"
        ),
    )
    op.create_table(
        "group",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=75), nullable=False),
        sa.Column("user_group", sa.BOOLEAN(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "group_memberships",
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("group_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["group.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("user_id", "group_id"),
    )
    op.create_table(
        "group_server_token_limits",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("latest_end", sa.DATETIME(), nullable=False),
        sa.Column("longest_life", sa.INTEGER(), nullable=False),
        sa.Column("server_id", sa.INTEGER(), nullable=False),
        sa.Column("group_id", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["group.id"],
        ),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["server.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "server_id", name="_group_server_limits_uc"),
    )
    op.create_table(
        "server_capability",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("server_id", sa.INTEGER(), nullable=False),
        sa.Column("capability", sa.TEXT(), nullable=False),
        sa.Column("capability_hash", sa.VARCHAR(length=32), nullable=False),
        sa.Column("enabled", sa.BOOLEAN(), nullable=True),
        sa.ForeignKeyConstraint(
            ["server_id"],
            ["server.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "capability_hash", name="_server_cap_uc"),
    )
    op.drop_table("users_with_roles")
    op.drop_table("scopes_in_role")
    op.drop_table("token_history")
    op.drop_table("scope")
    op.drop_table("role")
    # ### end Alembic commands ###
