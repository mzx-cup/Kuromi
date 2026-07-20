"""add subjects, chapters, subchapters, knowledge_points and extend courses

Revision ID: 20260529_add_course_hierarchy
Revises: b01b4224a404
Create Date: 2026-05-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '20260529_add_course_hierarchy'
down_revision: Union[str, Sequence[str], None] = 'b01b4224a404'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # subjects
    op.create_table('subjects',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('icon', sa.String(length=32), nullable=False),
        sa.Column('visible', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Add columns to existing courses table
    op.add_column('courses', sa.Column('subject_id', sa.String(length=64), nullable=False, server_default=''))
    op.add_column('courses', sa.Column('bvid', sa.String(length=32), nullable=False, server_default=''))
    op.add_column('courses', sa.Column('playlist_url', sa.String(length=512), nullable=False, server_default=''))
    op.add_column('courses', sa.Column('cover_url', sa.String(length=512), nullable=False, server_default=''))
    op.add_column('courses', sa.Column('author_name', sa.String(length=128), nullable=False, server_default=''))
    op.add_column('courses', sa.Column('total_lessons', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('courses', sa.Column('total_duration', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('courses', sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('courses', sa.Column('visible', sa.Boolean(), nullable=False, server_default='1'))
    op.add_column('courses', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'))
    op.create_foreign_key('fk_course_subject', 'courses', 'subjects', ['subject_id'], ['id'])

    # chapters
    op.create_table('chapters',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('course_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'])
    )

    # subchapters
    op.create_table('subchapters',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('chapter_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('bvid', sa.String(length=32), nullable=False),
        sa.Column('cid', sa.Integer(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False),
        sa.Column('transcript', sa.Text(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'])
    )

    # knowledge_points
    op.create_table('knowledge_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('subchapter_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=16), nullable=False),
        sa.Column('mastered', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['subchapter_id'], ['subchapters.id'])
    )


def downgrade() -> None:
    op.drop_table('knowledge_points')
    op.drop_table('subchapters')
    op.drop_table('chapters')
    op.drop_column('courses', 'subject_id')
    op.drop_column('courses', 'bvid')
    op.drop_column('courses', 'playlist_url')
    op.drop_column('courses', 'cover_url')
    op.drop_column('courses', 'author_name')
    op.drop_column('courses', 'total_lessons')
    op.drop_column('courses', 'total_duration')
    op.drop_column('courses', 'progress')
    op.drop_column('courses', 'visible')
    op.drop_column('courses', 'sort_order')
    op.drop_table('subjects')
