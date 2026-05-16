"""Messaging routes: campaigns, templates, groups, delivery tracking."""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.messaging_finance import Message, MessageTemplate, RecipientGroup, RecipientGroupMember, MessageDeliveryLog
from app.schemas.common import MessageCreate, MessageResponse, RecipientGroupCreate, MessageTemplateCreate
from app.dependencies import get_current_user, require_coordinator

router = APIRouter()


@router.get("/messages", response_model=list[MessageResponse])
async def list_messages(
    message_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = select(Message)
    if message_type:
        query = query.where(Message.message_type == message_type)
    query = query.order_by(Message.created_at.desc()).offset((page-1)*per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(body: MessageCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    msg = Message(sender_user_id=user.user_id, **body.model_dump())
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


@router.get("/messages/{message_id}/delivery-stats")
async def delivery_stats(message_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(
        select(MessageDeliveryLog.delivery_status, func.count())
        .where(MessageDeliveryLog.message_id == message_id)
        .group_by(MessageDeliveryLog.delivery_status)
    )
    return {"delivery_breakdown": {str(row[0]): row[1] for row in result.all()}}


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def create_template(body: MessageTemplateCreate, db: AsyncSession = Depends(get_db), user=Depends(require_coordinator)):
    tpl = MessageTemplate(created_by_user_id=user.user_id, **body.model_dump())
    db.add(tpl)
    await db.flush()
    return {"template_id": str(tpl.template_id), "message": "Template created"}


@router.get("/templates")
async def list_templates(db: AsyncSession = Depends(get_db), _user=Depends(get_current_user)):
    result = await db.execute(select(MessageTemplate).order_by(MessageTemplate.created_at.desc()))
    return [
        {"template_id": str(t.template_id), "template_name": t.template_name, "category": t.category}
        for t in result.scalars().all()
    ]


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_group(body: RecipientGroupCreate, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    group = RecipientGroup(**body.model_dump())
    db.add(group)
    await db.flush()
    return {"group_id": str(group.group_id), "message": "Group created"}


@router.post("/groups/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_group_member(group_id: UUID, voter_id: UUID, db: AsyncSession = Depends(get_db), _user=Depends(require_coordinator)):
    member = RecipientGroupMember(group_id=group_id, voter_id=voter_id, source="manual")
    db.add(member)
    # Update member count
    group = (await db.execute(select(RecipientGroup).where(RecipientGroup.group_id == group_id))).scalar_one_or_none()
    if group:
        count = (await db.execute(
            select(func.count()).select_from(RecipientGroupMember).where(RecipientGroupMember.group_id == group_id)
        )).scalar()
        group.member_count = count + 1
    await db.flush()
    return {"message": "Member added"}
