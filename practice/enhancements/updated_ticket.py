# Add these new endpoints to your existing tickets.py

@router.get("/ticket/{ticket_id}", response_class=HTMLResponse)
async def view_ticket(
    request: Request,
    ticket_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View function for individual ticket page"""
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
            detail="Not authorized to view this ticket"
        )
    
    # Get all responses for this ticket
    responses = db.query(models.TicketResponse) \
                 .filter(models.TicketResponse.ticket_id == ticket_id) \
                 .order_by(models.TicketResponse.created_at.asc()) \
                 .all()
    
    return templates.TemplateResponse(
        "customer/ticket_detail.html",
        {
            "request": request,
            "ticket": ticket,
            "responses": responses,
            "current_user": current_user
        }
    )

@router.post("/ticket/{ticket_id}/response")
async def add_ticket_response_view(
    request: Request,
    ticket_id: int,
    message: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View function for adding a response to a ticket"""
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
            message=message
        )
        db.add(new_response)
        
        # Update ticket status if responder is support agent
        if current_user.role == models.UserRole.support_agent and ticket.status == models.TicketStatus.open:
            ticket.status = models.TicketStatus.in_progress
        
        db.commit()
        return RedirectResponse(
            url=f"/ticket/{ticket_id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url=f"/ticket/{ticket_id}?error=Failed to add response",
            status_code=status.HTTP_302_FOUND
        )

@router.post("/create-ticket", response_class=RedirectResponse)
async def create_ticket_view(
    request: Request,
    subject: str = Form(...),
    description: str = Form(...),
    priority: str = Form(...),
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    """View function for creating a new ticket"""
    try:
        new_ticket = models.Ticket(
            user_id=current_user.id,
            subject=subject,
            description=description,
            priority=priority,
            status=models.TicketStatus.open
        )
        db.add(new_ticket)
        db.commit()
        
        # Create initial response from the ticket description
        initial_response = models.TicketResponse(
            ticket_id=new_ticket.id,
            responder_id=current_user.id,
            message=f"Ticket created: {description}"
        )
        db.add(initial_response)
        db.commit()
        
        return RedirectResponse(
            url=f"/ticket/{new_ticket.id}",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url="/dashboard?error=Failed to create ticket",
            status_code=status.HTTP_302_FOUND
        )