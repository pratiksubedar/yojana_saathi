"""
Yojana Saathi - Provenance and Freshness Service
Milestone 5.4: Formal verification metadata, source citation tracking,
and configurable temporal freshness analysis.

Core Principles:
1. Every scheme must have traceable official sources.
2. Temporal freshness is calculated from authoritative guideline verification/review dates,
   never inferred merely from transient web URL accessibility.
3. The freshness service NEVER upgrades unverified information to verified status automatically.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.db.models import Scheme
from app.schemas.provenance import (
    VerificationStatus,
    FreshnessStatus,
    PrimarySourceCitationSchema,
    VerificationMetadataSchema,
    FreshnessMetadataSchema,
    DocumentSourceSchema,
    OfficialPortalSchema,
    SchemeProvenanceResponse,
    SchemeFreshnessItem,
    CatalogFreshnessSummaryResponse,
)


@dataclass
class FreshnessConfig:
    """Configurable freshness evaluation parameters."""
    review_due_days: int = 90
    stale_days: int = 365
    reference_date: Optional[date] = None


def _parse_iso_date(date_str: Optional[str]) -> Optional[date]:
    """Safely parses an ISO date string (YYYY-MM-DD) into a date object."""
    if not date_str or not isinstance(date_str, str):
        return None
    clean = date_str.strip()
    if not clean:
        return None
    try:
        # Support YYYY-MM-DD or standard ISO strings
        return datetime.fromisoformat(clean).date()
    except (ValueError, TypeError):
        return None


class FreshnessService:
    """
    Evaluates source provenance traceability, factual verification levels,
    and temporal freshness for welfare schemes.
    """

    @classmethod
    def calculate_freshness(
        cls,
        verified_date_str: Optional[str],
        reviewed_date_str: Optional[str],
        verification_status: Any,
        config: Optional[FreshnessConfig] = None,
    ) -> FreshnessMetadataSchema:
        """
        Calculates the temporal freshness status of scheme guidelines.
        Enforces that unverified information is NEVER upgraded to verified/current status.
        """
        if config is None:
            config = FreshnessConfig()

        ref_date = config.reference_date or date.today()

        # Normalize verification status
        if isinstance(verification_status, VerificationStatus):
            v_status = verification_status
        else:
            raw_v_status = str(getattr(verification_status, "value", verification_status) or "").strip().upper()
            try:
                v_status = VerificationStatus(raw_v_status)
            except ValueError:
                v_status = VerificationStatus.UNVERIFIED

        # Parse dates
        v_date = _parse_iso_date(verified_date_str)
        r_date = _parse_iso_date(reviewed_date_str) or v_date

        days_since_v = (ref_date - v_date).days if v_date else None
        days_since_r = (ref_date - r_date).days if r_date else None

        # 1. Guard: Check for future dates (invalid metadata)
        if (days_since_v is not None and days_since_v < 0) or (days_since_r is not None and days_since_r < 0):
            future_date = reviewed_date_str if (days_since_r is not None and days_since_r < 0) else verified_date_str
            return FreshnessMetadataSchema(
                status=FreshnessStatus.UNVERIFIED,
                days_since_verification=days_since_v,
                days_since_review=days_since_r,
                review_due_threshold_days=config.review_due_days,
                stale_threshold_days=config.stale_days,
                reason=f"Verification or review date '{future_date}' is in the future and cannot be authoritatively confirmed.",
                is_fresh=False,
            )

        # 2. Guard: Missing or unparseable dates
        if not r_date or not v_date:
            return FreshnessMetadataSchema(
                status=FreshnessStatus.UNVERIFIED,
                days_since_verification=days_since_v,
                days_since_review=days_since_r,
                review_due_threshold_days=config.review_due_days,
                stale_threshold_days=config.stale_days,
                reason="Authoritative verification or review date is missing or invalid in scheme provenance records.",
                is_fresh=False,
            )

        # 3. Guard: Never upgrade unverified information to CURRENT/VERIFIED
        if v_status in (VerificationStatus.REQUIRES_OFFICIAL_VERIFICATION, VerificationStatus.UNVERIFIED):
            return FreshnessMetadataSchema(
                status=FreshnessStatus.UNVERIFIED,
                days_since_verification=days_since_v,
                days_since_review=days_since_r,
                review_due_threshold_days=config.review_due_days,
                stale_threshold_days=config.stale_days,
                reason="Scheme guidelines require official government verification before they can be certified as current.",
                is_fresh=False,
            )

        # 4. Temporal Evaluation based on review interval (VERIFIED or PARTIALLY_VERIFIED)
        assert days_since_r is not None

        if days_since_r <= config.review_due_days:
            if v_status == VerificationStatus.PARTIALLY_VERIFIED:
                reason = (
                    f"Reviewed {days_since_r} day(s) ago (within {config.review_due_days}-day review threshold); "
                    "contains partially verified criteria requiring local authority confirmation."
                )
            else:
                reason = (
                    f"Authoritatively verified and reviewed {days_since_r} day(s) ago "
                    f"(within {config.review_due_days}-day review threshold)."
                )
            return FreshnessMetadataSchema(
                status=FreshnessStatus.CURRENT,
                days_since_verification=days_since_v,
                days_since_review=days_since_r,
                review_due_threshold_days=config.review_due_days,
                stale_threshold_days=config.stale_days,
                reason=reason,
                is_fresh=True,
            )

        elif days_since_r <= config.stale_days:
            return FreshnessMetadataSchema(
                status=FreshnessStatus.REVIEW_DUE,
                days_since_verification=days_since_v,
                days_since_review=days_since_r,
                review_due_threshold_days=config.review_due_days,
                stale_threshold_days=config.stale_days,
                reason=(
                    f"Last reviewed {days_since_r} days ago; exceeds standard review threshold of "
                    f"{config.review_due_days} days."
                ),
                is_fresh=False,
            )

        else:
            return FreshnessMetadataSchema(
                status=FreshnessStatus.STALE,
                days_since_verification=days_since_v,
                days_since_review=days_since_r,
                review_due_threshold_days=config.review_due_days,
                stale_threshold_days=config.stale_days,
                reason=(
                    f"Outdated: last reviewed {days_since_r} days ago (exceeds stale threshold of "
                    f"{config.stale_days} days); authoritative guideline re-verification required."
                ),
                is_fresh=False,
            )

    @classmethod
    def build_scheme_provenance(
        cls,
        scheme: Scheme,
        config: Optional[FreshnessConfig] = None,
    ) -> SchemeProvenanceResponse:
        """
        Builds the complete provenance and freshness response model for a scheme.
        Safely extracts source citations, verification status, unresolved criteria,
        and supporting document origins.
        """
        citation_raw: Dict[str, Any] = scheme.source_citation if isinstance(scheme.source_citation, dict) else {}

        # 1. Primary Source Citation
        primary_source = PrimarySourceCitationSchema(
            title=citation_raw.get("title", f"{scheme.id.upper()} Official Guidelines"),
            url=citation_raw.get("url", scheme.official_url),
            issuing_authority=citation_raw.get("issuing_authority", scheme.ministry),
            scheme_version=citation_raw.get("scheme_version"),
            relevant_sections=citation_raw.get("relevant_sections", []),
        )

        # 2. Verification Metadata & Rule Completeness
        rule_completeness = "COMPLETE"
        unresolved_criteria: List[Dict[str, Any]] = []
        if scheme.rules and len(scheme.rules) > 0:
            first_rule = scheme.rules[0]
            conds = first_rule.conditions if isinstance(first_rule.conditions, dict) else {}
            rule_completeness = conds.get("rule_completeness", "COMPLETE")
            raw_unresolved = conds.get("unresolved_criteria", [])
            unresolved_criteria = [
                item if isinstance(item, dict) else {"criterion": str(item), "status": "REQUIRES_OFFICIAL_VERIFICATION"}
                for item in raw_unresolved
            ]

        # Fallback to source_citation if not in rule conditions
        raw_status = citation_raw.get("verification_status")
        if not raw_status:
            raw_status = "PARTIALLY_VERIFIED" if rule_completeness == "PARTIAL" else "VERIFIED"

        try:
            v_status = VerificationStatus(str(raw_status).upper())
        except ValueError:
            v_status = VerificationStatus.UNVERIFIED

        verified_date = citation_raw.get("verified_date") or scheme.last_verified_date
        reviewed_date = citation_raw.get("last_reviewed_date") or getattr(scheme, "last_reviewed_date", scheme.last_verified_date)

        verification_meta = VerificationMetadataSchema(
            verification_status=v_status,
            last_verified_date=verified_date,
            last_reviewed_date=reviewed_date,
            rule_completeness=rule_completeness,
            unresolved_criteria=unresolved_criteria,
        )

        # 3. Freshness Assessment
        freshness_meta = cls.calculate_freshness(
            verified_date_str=verified_date,
            reviewed_date_str=reviewed_date,
            verification_status=v_status,
            config=config,
        )

        # 4. Document Sources
        doc_sources: List[DocumentSourceSchema] = []
        if scheme.documents:
            for d in scheme.documents:
                doc_sources.append(
                    DocumentSourceSchema(
                        document_id=d.id,
                        names=d.names if isinstance(d.names, dict) else {},
                        issuer=d.issuer or "Government Authority",
                        source_url=getattr(d, "source_url", None),
                        is_mandatory=d.is_mandatory,
                    )
                )

        return SchemeProvenanceResponse(
            scheme_id=scheme.id,
            names=scheme.names if isinstance(scheme.names, dict) else {},
            ministry=scheme.ministry,
            official_portal=OfficialPortalSchema(
                url=scheme.official_url,
                portal_name=scheme.portal_name,
            ),
            primary_source=primary_source,
            verification=verification_meta,
            freshness=freshness_meta,
            document_sources=doc_sources,
        )

    @classmethod
    def get_catalog_freshness_summary(
        cls,
        schemes: List[Scheme],
        config: Optional[FreshnessConfig] = None,
    ) -> CatalogFreshnessSummaryResponse:
        """
        Computes aggregate catalog-level freshness and audit summary across all active schemes.
        """
        if config is None:
            config = FreshnessConfig()

        items: List[SchemeFreshnessItem] = []
        counts = {
            FreshnessStatus.CURRENT: 0,
            FreshnessStatus.REVIEW_DUE: 0,
            FreshnessStatus.STALE: 0,
            FreshnessStatus.UNVERIFIED: 0,
        }

        for s in schemes:
            citation_raw = s.source_citation if isinstance(s.source_citation, dict) else {}
            v_status_str = citation_raw.get("verification_status") or "VERIFIED"
            try:
                v_status = VerificationStatus(str(v_status_str).upper())
            except ValueError:
                v_status = VerificationStatus.UNVERIFIED

            v_date = citation_raw.get("verified_date") or s.last_verified_date
            r_date = citation_raw.get("last_reviewed_date") or getattr(s, "last_reviewed_date", s.last_verified_date)

            freshness = cls.calculate_freshness(
                verified_date_str=v_date,
                reviewed_date_str=r_date,
                verification_status=v_status,
                config=config,
            )

            counts[freshness.status] += 1

            name_en = s.names.get("en", s.id) if isinstance(s.names, dict) else s.id

            items.append(
                SchemeFreshnessItem(
                    scheme_id=s.id,
                    scheme_name_en=name_en,
                    freshness_status=freshness.status,
                    verification_status=v_status,
                    last_verified_date=v_date,
                    last_reviewed_date=r_date,
                    days_since_review=freshness.days_since_review,
                    is_fresh=freshness.is_fresh,
                    reason=freshness.reason,
                )
            )

        return CatalogFreshnessSummaryResponse(
            total_schemes=len(schemes),
            current_count=counts[FreshnessStatus.CURRENT],
            review_due_count=counts[FreshnessStatus.REVIEW_DUE],
            stale_count=counts[FreshnessStatus.STALE],
            unverified_count=counts[FreshnessStatus.UNVERIFIED],
            review_due_threshold_days=config.review_due_days,
            stale_threshold_days=config.stale_days,
            items=items,
        )
