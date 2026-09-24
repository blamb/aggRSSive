from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_slug(n: int = 8) -> str:
    return secrets.token_urlsafe(n)[:n].lower().replace("-", "x").replace("_", "y")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(back_populates="user", cascade="all, delete-orphan")
    bundles: Mapped[list[Bundle]] = relationship(back_populates="owner")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(32))
    provider_user_id: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="oauth_accounts")


# --- Sources, items, tags -------------------------------------------------

source_tags = Table(
    "source_tags",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), default=utcnow),
)


class Source(Base):
    """A feed. Shared across all users; anyone may tag it or bundle it."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    site_url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(32), default="feed")  # feed | (later) adapter kinds
    added_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # fetch state
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Tag suggestions awaiting a human decision; newline separated. Rejected ones are remembered so they don't come back.
    suggested_tags: Mapped[str] = mapped_column(Text, default="")
    rejected_tags: Mapped[str] = mapped_column(Text, default="")
    # Classification proposals awaiting a decision, as "framework:code" lines; rejected ones remembered.
    suggested_categories: Mapped[str] = mapped_column(Text, default="")
    rejected_categories: Mapped[str] = mapped_column(Text, default="")
    # Set when the person adding the source asked for GenAI suggestions; consumed after the first fetch.
    ai_pending: Mapped[bool] = mapped_column(Boolean, default=False)

    categories: Mapped[list[Category]] = relationship(secondary="source_categories", back_populates="sources")
    items: Mapped[list[Item]] = relationship(back_populates="source", cascade="all, delete-orphan")
    tags: Mapped[list[Tag]] = relationship(secondary=source_tags, back_populates="sources")
    rules: Mapped[list[Rule]] = relationship(
        primaryjoin="and_(Rule.owner_type=='source', foreign(Rule.owner_id)==Source.id)",
        viewonly=True,
    )
    added_by: Mapped[User | None] = relationship()


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("source_id", "guid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    guid: Mapped[str] = mapped_column(String(2048))
    url: Mapped[str] = mapped_column(String(2048), index=True)
    title: Mapped[str] = mapped_column(String(1000), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(Text, default="")  # sanitized HTML
    content: Mapped[str] = mapped_column(Text, default="")  # sanitized HTML, may be empty
    text: Mapped[str] = mapped_column(Text, default="")  # plain text for filtering
    image_url: Mapped[str | None] = mapped_column(String(2048))
    categories: Mapped[str] = mapped_column(Text, default="")  # newline separated
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    source: Mapped[Source] = relationship(back_populates="items")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sources: Mapped[list[Source]] = relationship(secondary=source_tags, back_populates="tags")


# --- Classification (controlled vocabularies, alongside free tags) ------------

source_categories = Table(
    "source_categories",
    Base.metadata,
    Column("source_id", ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", DateTime(timezone=True), default=utcnow),
)


class Category(Base):
    """One node of a classification framework (LCC subclass, ISCED-F field, ...). Seeded from data files."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("framework", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    framework: Mapped[str] = mapped_column(String(16), index=True)  # lcc | isced
    code: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(300))
    parent_code: Mapped[str | None] = mapped_column(String(16))
    depth: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, default=0)

    sources: Mapped[list[Source]] = relationship(secondary=source_categories, back_populates="categories")


# --- Bundles and rules ------------------------------------------------------

bundle_sources = Table(
    "bundle_sources",
    Base.metadata,
    Column("bundle_id", ForeignKey("bundles.id", ondelete="CASCADE"), primary_key=True),
    Column("source_id", ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
    Column("position", Integer, default=0),
)


class Bundle(Base):
    """An aggRSSive: a curated set of sources plus filtering rules."""

    __tablename__ = "bundles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=new_slug)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # rule semantics
    match_mode: Mapped[str] = mapped_column(String(8), default="any")  # any | all  (for include rules)
    max_age_days: Mapped[int | None] = mapped_column(Integer)
    max_items: Mapped[int] = mapped_column(Integer, default=50)
    dedupe: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped[User] = relationship(back_populates="bundles")
    sources: Mapped[list[Source]] = relationship(secondary=bundle_sources, order_by=bundle_sources.c.position)
    rules: Mapped[list[Rule]] = relationship(
        primaryjoin="and_(Rule.owner_type=='bundle', foreign(Rule.owner_id)==Bundle.id)",
        viewonly=True,
    )
    overrides: Mapped[list[ItemOverride]] = relationship(back_populates="bundle", cascade="all, delete-orphan")


class Rule(Base):
    """A filter rule attached to a source (applies everywhere) or a bundle."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(8), index=True)  # source | bundle
    owner_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(8))  # include | exclude
    field: Mapped[str] = mapped_column(String(16), default="any")  # any|title|text|author|url|category
    pattern: Mapped[str] = mapped_column(String(500))
    is_regex: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Platform(Base):
    """An LTI 1.3 platform (a Moodle, Canvas, ... site) registered with this tool."""

    __tablename__ = "lti_platforms"
    __table_args__ = (UniqueConstraint("issuer", "client_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    issuer: Mapped[str] = mapped_column(String(500), index=True)
    client_id: Mapped[str] = mapped_column(String(255))
    auth_login_url: Mapped[str] = mapped_column(String(1000))  # OIDC authorization endpoint
    auth_token_url: Mapped[str] = mapped_column(String(1000), default="")
    jwks_url: Mapped[str] = mapped_column(String(1000))
    deployment_ids: Mapped[str] = mapped_column(Text, default="")  # newline separated, learned from launches
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_launch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LtiState(Base):
    """One-time OIDC state/nonce for a launch in flight. Server-side, so no third-party cookie is needed."""

    __tablename__ = "lti_states"

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonce: Mapped[str] = mapped_column(String(64))
    platform_id: Mapped[int] = mapped_column(ForeignKey("lti_platforms.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ItemOverride(Base):
    """Manual curation inside a bundle: pin, hide, annotate a specific item."""

    __tablename__ = "item_overrides"
    __table_args__ = (UniqueConstraint("bundle_id", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bundle_id: Mapped[int] = mapped_column(ForeignKey("bundles.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")

    bundle: Mapped[Bundle] = relationship(back_populates="overrides")
    item: Mapped[Item] = relationship()
