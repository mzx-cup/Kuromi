"""add demo flags + lecture/mindmap/slides JSON fields

Revision ID: 20260720_demo_flags
Revises: 20260529_add_course_hierarchy
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON as MySQL_JSON

# revision identifiers, used by Alembic.
revision = "20260720_demo_flags"
down_revision = "20260529_add_course_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = MySQL_JSON if bind.dialect.name == "mysql" else sa.Text

    # subjects
    op.add_column("subjects", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("subjects", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # courses
    op.add_column("courses", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("courses", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # chapters (also adds lecture + mindmap)
    op.add_column("chapters", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("chapters", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("chapters", sa.Column("lecture", json_type, nullable=True))
    op.add_column("chapters", sa.Column("mindmap", json_type, nullable=True))

    # subchapters
    op.add_column("subchapters", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("subchapters", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))

    # classroom_sessions (also adds slides)
    op.add_column("classroom_sessions", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default="0"))
    op.add_column("classroom_sessions", sa.Column("demo_version", sa.String(16), nullable=False, server_default=""))
    op.add_column("classroom_sessions", sa.Column("slides", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("classroom_sessions", "slides")
    op.drop_column("classroom_sessions", "demo_version")
    op.drop_column("classroom_sessions", "is_demo")
    op.drop_column("subchapters", "demo_version")
    op.drop_column("subchapters", "is_demo")
    op.drop_column("chapters", "mindmap")
    op.drop_column("chapters", "lecture")
    op.drop_column("chapters", "demo_version")
    op.drop_column("chapters", "is_demo")
    op.drop_column("courses", "demo_version")
    op.drop_column("courses", "is_demo")
    op.drop_column("subjects", "demo_version")
    op.drop_column("subjects", "is_demo")