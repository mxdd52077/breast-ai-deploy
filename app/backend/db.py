from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import NullPool

APP_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(APP_ROOT / ".env", override=False)
default_data_dir = Path("/tmp/apex-care") if os.getenv("VERCEL") else APP_ROOT / "private-data"
DATA = Path(os.getenv("APEX_DATA_DIR", str(default_data_dir))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA / 'apex.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL="postgresql+psycopg://"+DATABASE_URL.removeprefix("postgres://")
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL="postgresql+psycopg://"+DATABASE_URL.removeprefix("postgresql://")
options={"pool_pre_ping":True}
if DATABASE_URL.startswith("sqlite"):
    options["connect_args"]={"check_same_thread":False,"timeout":30}
elif os.getenv("VERCEL"):
    options["connect_args"]={"prepare_threshold":None}
    options["poolclass"]=NullPool
engine=create_engine(DATABASE_URL,**options)
if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def sqlite_config(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

Session = sessionmaker(engine, expire_on_commit=False)

def uid():
    return uuid.uuid4().hex

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(60))
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    institution_access: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf: Mapped[str] = mapped_column(String(64))
    expires: Mapped[float] = mapped_column(Float)

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("user_id", "digest"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    digest: Mapped[str] = mapped_column(String(64))
    extension: Mapped[str] = mapped_column(String(10))
    size: Mapped[int] = mapped_column(Integer)
    pages: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    error: Mapped[str] = mapped_column(Text, default="")
    method: Mapped[str] = mapped_column(String(60), default="")
    report_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), unique=True)
    state: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    lease: Mapped[float] = mapped_column(Float, default=0)
    claim: Mapped[str] = mapped_column(String(32), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)

class Fact(Base):
    __tablename__ = "facts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    page: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    scheduled_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scheduled_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    scheduled_end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    scheduled_end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    schedule_basis: Mapped[str] = mapped_column(Text, default="")
    conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    fact_id: Mapped[str | None] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"), unique=True, nullable=True)
    page: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(120), default="")
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    embedding_model: Mapped[str] = mapped_column(String(40), default="apex-zh-char-v1")
    embedding: Mapped[list | None] = mapped_column(Vector(384).with_variant(JSON, "sqlite"), nullable=True)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    fact_id: Mapped[str] = mapped_column(ForeignKey("facts.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(Text)
    due_date: Mapped[str] = mapped_column(String(10))
    due_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    due_end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    due_end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    category: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated: Mapped[float] = mapped_column(Float, default=time.time)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(12))
    text: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    action_fact_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="supported")
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    resource: Mapped[str] = mapped_column(String(32))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class Simulation(Base):
    __tablename__ = "simulations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    inputs: Mapped[dict] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)
    analysis: Mapped[dict] = mapped_column(JSON)
    created: Mapped[float] = mapped_column(Float, default=time.time)

def init_db():
    Base.metadata.create_all(engine)

def audit(db, user_id, action, resource, detail=None):
    db.add(Audit(user_id=user_id,action=action,resource=resource,detail=detail or {}))
