# Add these new routes to your existing frontend.py

@router.get("/dashboard/my_tickets", response_class=HTMLResponse)
async def get_my_tickets(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1
):
    """View function for My Tickets page"""
    if current_user.role != models.UserRole.customer:
        return RedirectResponse(url="/dashboard")
    
    # Get tickets with pagination
    per_page = 10
    query = db.query(models.Ticket).filter(models.Ticket.user_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    
    total_tickets = query.count()
    tickets = query.order_by(models.Ticket.created_at.desc()) \
                  .offset((page - 1) * per_page) \
                  .limit(per_page) \
                  .all()
    
    return templates.TemplateResponse(
        "customer/customer_my_tickets.html",
        {
            "request": request,
            "user": current_user,
            "tickets": tickets,
            "current_page": page,
            "total_pages": (total_tickets // per_page) + (1 if total_tickets % per_page else 0),
            "status_filter": status,
            "priority_filter": priority
        }
    )

@router.get("/knowledge-base", response_class=HTMLResponse)
async def get_knowledge_base(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    search: Optional[str] = None
):
    """View function for Knowledge Base page"""
    # In a real app, you would query your knowledge base articles here
    categories = ["Getting Started", "Account Management", "Billing", "Troubleshooting"]
    
    # Mock articles - replace with actual database queries
    popular_articles = [
        {"title": "How to reset your password", "content": "Step-by-step guide to resetting your password"},
        {"title": "Understanding user roles", "content": "Learn about different user permissions"}
    ]
    
    return templates.TemplateResponse(
        "customer/knowledge_base.html",
        {
            "request": request,
            "user": current_user,
            "categories": categories,
            "popular_articles": popular_articles,
            "search_query": search
        }
    )

@router.get("/settings", response_class=HTMLResponse)
async def get_settings(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie)
):
    """View function for Settings page"""
    return templates.TemplateResponse(
        "customer/settings.html",
        {
            "request": request,
            "user": current_user
        }
    )

@router.post("/settings/update", response_class=RedirectResponse)
async def update_settings(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db),
    name: str = Form(None),
    email: str = Form(None),
    notifications: str = Form(None)
):
    """Update user settings"""
    try:
        if name:
            current_user.name = name
        if email:
            # Check if email is already taken
            existing_user = db.query(models.User).filter(
                models.User.email == email,
                models.User.id != current_user.id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
            current_user.email = email
        
        db.commit()
        return RedirectResponse(
            url="/settings?message=Settings updated successfully",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        db.rollback()
        return RedirectResponse(
            url="/settings?error=Failed to update settings",
            status_code=status.HTTP_302_FOUND
        )