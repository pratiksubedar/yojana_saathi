from fastapi import APIRouter
from app.api.v1 import health, schemes, eligibility, documents, chat

api_router = APIRouter()

# Register API v1 sub-routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(schemes.router, tags=["Schemes Catalog"])
api_router.include_router(eligibility.router, tags=["Eligibility Engine"])
api_router.include_router(documents.router, tags=["Document Checklist"])
api_router.include_router(chat.router, tags=["Conversational Chat"])


