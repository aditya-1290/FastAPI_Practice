from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, tickets, frontend
from database import engine, Base
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import logging

#Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
        
app = FastAPI(
    title="Customer Support and Feedback System",
    description="API for managing customer support tickets",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

#CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#Create database tables(only in development)
if os.getenv("APP_ENV","development")== "development":
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created Successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        
# Mount Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Templates
templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Include Routers
app.include_router(frontend.router)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

       