"""SMS broadcast endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user, require_coordinator
from app.models.auth import User
from app.models.sms import SmsBroadcast
from app.models.voters import Voter
from app.services.sms_service import send_sms

router = APIRouter()


@router.post("/send", status_code=status.HTTP_201_CREATED)
async def send_broadcast(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_coordinator),
):
    """Send SMS broadcast to voters with optional filters"""
    message = body.get("message", "").strip()
    title = body.get("title", "Broadcast")
    constituency_id = body.get("constituency_id")
    ward_id = body.get("ward_id")
    support_level = body.get("support_level")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    if len(message) > 480:
        raise HTTPException(status_code=400, detail="Message too long (max 480 chars / 3 SMS)")
    
    # Build query with filters
    query = select(Voter).where(Voter.phone_number.isnot(None))
    if constituency_id:
        query = query.where(Voter.constituency_id == constituency_id)
    if ward_id:
        query = query.where(Voter.ward_id == ward_id)
    if support_level:
        query = query.where(Voter.support_level == support_level)
    
    result = await db.execute(query)
    voters = result.scalars().all()
    
    phones = [v.phone_number for v in voters if v.phone_number]
    if not phones:
        raise HTTPException(status_code=400, detail="No voters match the filter criteria")
    
    # Send SMS
    sms_result = send_sms(phones, message)
    
    # Calculate stats from response
    successful = 0
    failed = 0
    if sms_result.get("success"):
        recipients = sms_result.get("response", {}).get("SMSMessageData", {}).get("Recipients", [])
        for r in recipients:
            if r.get("status") == "Success":
                successful += 1
            else:
                failed += 1
    else:
        failed = len(phones)
    
    # Log broadcast
    broadcast = SmsBroadcast(
        title=title,
        message=message,
        filter_constituency_id=constituency_id,
        filter_ward_id=ward_id,
        filter_support_level=support_level,
        total_recipients=len(phones),
        successful_sends=successful,
        failed_sends=failed,
        api_response=sms_result,
        sent_by_user_id=user.user_id,
    )
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)
    
    return {
        "broadcast_id": broadcast.broadcast_id,
        "total_recipients": len(phones),
        "successful": successful,
        "failed": failed,
        "success": sms_result.get("success", False),
        "error": sms_result.get("error"),
    }


@router.get("/history")
async def get_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get SMS broadcast history"""
    result = await db.execute(
        select(SmsBroadcast).order_by(SmsBroadcast.sent_at.desc()).limit(limit)
    )
    broadcasts = result.scalars().all()
    return [
        {
            "broadcast_id": b.broadcast_id,
            "title": b.title,
            "message": b.message,
            "total_recipients": b.total_recipients,
            "successful_sends": b.successful_sends,
            "failed_sends": b.failed_sends,
            "sent_at": b.sent_at.isoformat() if b.sent_at else None,
        }
        for b in broadcasts
    ]


@router.get("/preview-count")
async def preview_count(
    constituency_id: str = None,
    ward_id: str = None,
    support_level: str = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preview how many voters will receive SMS"""
    query = select(Voter).where(Voter.phone_number.isnot(None))
    if constituency_id:
        query = query.where(Voter.constituency_id == constituency_id)
    if ward_id:
        query = query.where(Voter.ward_id == ward_id)
    if support_level:
        query = query.where(Voter.support_level == support_level)
    
    result = await db.execute(query)
    count = len(result.scalars().all())
    estimated_cost_kes = count * 0.8
    return {"count": count, "estimated_cost_kes": estimated_cost_kes}
