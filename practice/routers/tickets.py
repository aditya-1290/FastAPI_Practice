from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Annotated
from datetime import datetime
import schemas, models
from database import get_db
from security import get_current_user
from fastapi import Query  
from pydantic import Field

router = APIRouter()

@router.post("/create_ticket", response_model=schemas.TicketResponseOut)
async def create_ticket(
    ticket: schemas.TicketCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):       
    """
    Create a new support ticket.
    """
    try:
        new_ticket = models.Ticket(
            user_id=current_user.id,
            subject=ticket.subject,
            description=ticket.description,
            priority=ticket.priority,
            status=models.TicketStatus.open
        )
        db.add(new_ticket)
        db.commit()
        db.refresh(new_ticket)
        
        # Create initial response from the ticket description
        initial_response = models.TicketResponse(
            ticket_id=new_ticket.id,
            responder_id=current_user.id,
            message=f"Ticket created: {ticket.description}"
        )
        db.add(initial_response)
        db.commit()
        
        return new_ticket
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ticket"
        )

@router.get("/get_tickets", response_model=List[schemas.TicketResponseOut])
async def get_tickets(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[models.TicketStatus] = Query(None),
    priority: Optional[str] = Query(None),
    # page: conint(ge=1) = 1,
    page: Annotated[int, Field(strict=True, gt=0)] = 1,
    per_page: Annotated[int, Field(strict=True, ge=1, le=100)] = 10,
    # per_page: conint(ge=1, le=100) = 10
):
    """
    Get list of tickets with pagination and filtering.
    """
    query = db.query(models.Ticket)
    
    # Apply filters based on user role
    if current_user.role == models.UserRole.customer:
        query = query.filter(models.Ticket.user_id == current_user.id)
    
    # Apply status filter if provided
    if status:
        query = query.filter(models.Ticket.status == status)
    
    # Apply priority filter if provided
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    
    # Apply pagination
    tickets = query.order_by(models.Ticket.created_at.desc()) \
                 .offset((page - 1) * per_page) \
                 .limit(per_page) \
                 .all()
    
    return tickets

@router.get("get_ticket_id/{ticket_id}", response_model=schemas.TicketResponseOut)
async def get_ticket(
    ticket_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific ticket.
    """
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Authorization check
    if current_user.role == models.UserRole.customer and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this ticket"
        )
    
    return ticket

@router.post("add_ticket_response/{ticket_id}/responses", response_model=schemas.TicketResponseResponse)
async def add_ticket_response(
    ticket_id: int,
    response: schemas.TicketResponseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a response to a ticket.
    """
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Authorization check
    if current_user.role != models.UserRole.support_agent and ticket.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add response to this ticket"
        )
    
    try:
        new_response = models.TicketResponse(
            ticket_id=ticket_id,
            responder_id=current_user.id,
            message=response.message
        )
        db.add(new_response)
        
        # Update ticket status if responder is support agent
        if current_user.role == models.UserRole.support_agent and ticket.status == models.TicketStatus.open:
            ticket.status = models.TicketStatus.in_progress
        
        db.commit()
        db.refresh(new_response)
        return new_response
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add response"
        )

@router.patch("update_ticket_status/{ticket_id}", response_model=schemas.TicketResponseOut)
async def update_ticket_status(
    ticket_id: int,
    ticket_update: schemas.TicketUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update ticket status (support agents only).
    """
    if current_user.role != models.UserRole.support_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only support agents can update ticket status"
        )
    
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    try:
        if ticket_update.status:
            ticket.status = ticket_update.status
        db.commit()
        db.refresh(ticket)
        return ticket
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket status"
        )
