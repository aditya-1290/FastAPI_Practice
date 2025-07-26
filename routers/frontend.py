
from fastapi import APIRouter, Request, Form, Depends, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from security import (
    get_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS, decode_token
)
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from datetime import timedelta

router = APIRouter()
templates = Jinja2Templates(directory="templates")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        token = token.split("Bearer ")[1]
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = db.query(models.User).filter(models.User.email == payload.get("sub")).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
def get_login(request: Request, message: str = None):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": request.query_params.get("error"),
            "message": message
        }
    )

@router.get("/register", response_class=HTMLResponse)
def get_register(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "error": request.query_params.get("error")
        }
    )

@router.post("/register")
async def post_register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    # Validate role
    if role not in ["customer", "support_agent"]:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Invalid role selected"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Email already registered"
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Create new user
    hashed_password = get_password(password)
    new_user = models.User(
        name=name,
        email=email,
        password_hash=hashed_password,
        role=models.UserRole(role)
    )
    
    try:
        db.add(new_user)
        db.commit()
        return RedirectResponse(
            url="/login?message=Registration successful. Please login.",
            status_code=status.HTTP_302_FOUND
        )
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Registration failed. Please try again."
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/login")
async def post_login(
    request: Request,
    response: RedirectResponse,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.password_hash) or user.role.value != role:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid credentials or role"
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # Create tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    # Set secure cookies
    redirect_response = RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_302_FOUND
    )
    redirect_response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    redirect_response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    return redirect_response

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, current_user: models.User = Depends(get_current_user_from_cookie)):
    if current_user.role == models.UserRole.customer:
        return templates.TemplateResponse(
            "customer_dashboard.html",
            {
                "request": request,
                "user": current_user  
            }
        )
    elif current_user.role == models.UserRole.support_agent:
        return templates.TemplateResponse(
            "support_agent_dashboard.html",
            {
                "request": request,
                "user": current_user
            }
        )
    else:
        return RedirectResponse(url="/login")

@router.get("/dashboard/my_tickets", response_class=HTMLResponse)
async def get_my_tickets(request: Request, current_user: models.User = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    if current_user.role != models.UserRole.customer:
        return RedirectResponse(url="/login")
    tickets = db.query(models.Ticket).filter(models.Ticket.user_id == current_user.id).order_by(models.Ticket.created_at.desc()).all()
    return templates.TemplateResponse(
        "customer_my_tickets.html",
        {
            "request": request,
            "user": current_user,
            "tickets": tickets
        }
    )

@router.get("/dashboard/knowledge_base", response_class=HTMLResponse)
async def get_knowledge_base(request: Request, current_user: models.User = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    if current_user.role != models.UserRole.customer:
        return RedirectResponse(url="/login")
    # For now, mock knowledge base articles
    articles = [
        {"id": 1, "title": "How to reset your password", "summary": "Steps to reset your password."},
        {"id": 2, "title": "How to create a support ticket", "summary": "Guide to create a support ticket."},
        {"id": 3, "title": "Contact support", "summary": "How to contact support team."}
    ]
    return templates.TemplateResponse(
        "customer_knowledge_base.html",
        {
            "request": request,
            "user": current_user,
            "articles": articles
        }
    )

@router.get("/dashboard/settings", response_class=HTMLResponse)
async def get_settings(request: Request, current_user: models.User = Depends(get_current_user_from_cookie)):
    if current_user.role != models.UserRole.customer:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "customer_settings.html",
        {
            "request": request,
            "user": current_user
        }
    )

@router.post("/dashboard/settings", response_class=HTMLResponse)
async def post_settings(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    current_user: models.User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if current_user.role != models.UserRole.customer:
        return RedirectResponse(url="/login")
    # Update user info
    current_user.name = name
    current_user.email = email
    try:
        db.add(current_user)
        db.commit()
        message = "Settings updated successfully."
    except Exception as e:
        db.rollback()
        message = "Failed to update settings."
    return templates.TemplateResponse(
        "customer_settings.html",
        {
            "request": request,
            "user": current_user,
            "message": message
        }
    )

@router.get("/logout")
async def logout(response: RedirectResponse):
    redirect_response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_302_FOUND
    )
    redirect_response.delete_cookie("access_token")
    redirect_response.delete_cookie("refresh_token")
    return redirect_response