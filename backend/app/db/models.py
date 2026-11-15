from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Scheme(Base, TimestampMixin):
    """
    Authoritative Welfare Scheme record.
    Stores multilingual titles, descriptions, benefits, and verified government portal URLs.
    """
    __tablename__ = "schemes"

    # Primary key (slug-based ID, e.g., 'pm-kisan', 'pm-jay')
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    ministry: Mapped[str] = mapped_column(String(255), nullable=False)
    scheme_type: Mapped[str] = mapped_column(String(64), default="CENTRAL_SECTOR", nullable=False)
    
    # State applicability: e.g. ["ALL"] or ["Karnataka", "Telangana"]
    state_applicability: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["ALL"], nullable=False)

    # Multilingual Content Fields: Dictionary mapping lang codes ('en', 'hi', 'kn', 'te') to text
    names: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    descriptions: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    benefits: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    financial_amount_inr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Official Government Links & Source Traceability
    official_url: Mapped[str] = mapped_column(String(512), nullable=False)
    portal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_verified_date: Mapped[str] = mapped_column(String(32), nullable=False)
    last_reviewed_date: Mapped[str] = mapped_column(String(32), default="2026-11-10", nullable=False)
    source_citation: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    application_procedure: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships (Cascade deletion ensures integrity when schemes are updated/removed)
    rules: Mapped[List["Rule"]] = relationship(
        "Rule",
        back_populates="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chunks: Mapped[List["SchemeChunk"]] = relationship(
        "SchemeChunk",
        back_populates="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Scheme(id='{self.id}', ministry='{self.ministry}')>"


class Rule(Base, TimestampMixin):
    """
    Deterministic Eligibility Rule definition for a Scheme.
    Contains the declarative JSON AST conditions ('all_of', 'any_of', 'none_of')
    and clause-level citations to official guidelines.
    """
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scheme_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(32), default="2026.1", nullable=False)
    
    # Declarative AST condition tree
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship back to scheme
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="rules")

    def __repr__(self) -> str:
        return f"<Rule(id={self.id}, scheme_id='{self.scheme_id}', version='{self.version}')>"


class Document(Base, TimestampMixin):
    """
    Required Document record for a Scheme.
    Specifies mandatory status, multilingual titles, descriptions, and CSC assistance guidance.
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scheme_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Multilingual Names and Guidance
    names: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    descriptions: Mapped[Dict[str, str]] = mapped_column(JSON, nullable=False)
    
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    csc_assisted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), default="Government Authority", nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Relationship back to scheme
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="documents")

    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', scheme_id='{self.scheme_id}', mandatory={self.is_mandatory})>"


class CitizenSession(Base):
    """
    Privacy-Conscious, Ephemeral Session Record.
    Adheres to Zero-Knowledge principles: does NOT persist citizen names, Aadhaar,
    bank accounts, phone numbers, or conversation transcripts.
    """
    __tablename__ = "citizen_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Anonymous UUID
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CitizenSession(id='{self.id}', lang='{self.language}')>"


class EphemeralChecklistItem(Base):
    """
    Privacy-Conscious Ephemeral Checklist State.
    Tracks boolean collection status for an anonymous session without storing citizen document contents or numbers.
    Has a 2-hour sliding window expiration policy from creation or last activity.
    """
    __tablename__ = "session_checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    scheme_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(64), nullable=False)
    is_collected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(hours=2),
        index=True,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EphemeralChecklistItem(session='{self.session_id}', doc='{self.document_id}', collected={self.is_collected})>"


class SchemeChunk(Base, TimestampMixin):
    """
    Structured semantic chunk of a welfare scheme for RAG retrieval.
    Preserves exact provenance metadata and distinguishes curated summaries
    from verbatim official text.
    """
    __tablename__ = "scheme_chunks"

    chunk_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    scheme_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    relevant_section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(64), default="VERIFIED", nullable=False)
    last_reviewed_date: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    content_type: Mapped[str] = mapped_column(String(64), default="curated_summary", nullable=False)
    is_verbatim: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship back to scheme
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<SchemeChunk(id='{self.chunk_id}', scheme='{self.scheme_id}', cat='{self.category}', lang='{self.language}')>"


