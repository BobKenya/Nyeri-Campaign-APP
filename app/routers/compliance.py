"""Compliance routes: documents, permits, IEBC reports, audit logs."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.messaging_finance import ComplianceDocument, PermitLicense, IEBCReport, AuditLog
from app.dependencies import get_current_user, require_admin

router = APIRouter()


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(ComplianceDocument).order_by(ComplianceDocument.filing_date.desc()))
    return [
        {
            "document_id": str(d.document_id), "document_type": d.document_type,
            "document_name": d.document_name, "filing_date": d.filing_date.isoformat() if d.filing_date else None,
            "iebc_submission_date": d.iebc_submission_date.isoformat() if d.iebc_submission_date else None,
        }
        for d in result.scalars().all()
    ]


@router.get("/permits")
async def list_permits(status_filter: Optional[str] = None, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    query = select(PermitLicense)
    if status_filter:
        query = query.where(PermitLicense.status == status_filter)
    result = await db.execute(query.order_by(PermitLicense.expiry_date))
    return [
        {
            "permit_id": str(p.permit_id), "permit_type": p.permit_type,
            "issuing_authority": p.issuing_authority, "status": p.status,
            "expiry_date": p.expiry_date.isoformat() if p.expiry_date else None,
        }
        for p in result.scalars().all()
    ]


@router.get("/iebc-reports")
async def list_iebc_reports(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(IEBCReport).order_by(IEBCReport.submission_date.desc()))
    return [
        {
            "report_id": str(r.report_id), "report_type": r.report_type,
            "total_spending": float(r.total_spending) if r.total_spending else 0,
            "compliance_status": r.compliance_status, "status": r.status,
        }
        for r in result.scalars().all()
    ]


@router.get("/audit-logs")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    user_id: Optional[UUID] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
):
    query = select(AuditLog)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    query = query.order_by(AuditLog.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return [
        {
            "log_id": str(l.log_id), "user_id": str(l.user_id) if l.user_id else None,
            "action_type": l.action_type, "entity_type": l.entity_type,
            "entity_id": str(l.entity_id) if l.entity_id else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in result.scalars().all()
    ]
