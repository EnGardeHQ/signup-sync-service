"""
Health check models
"""
from pydantic import BaseModel
from typing import Optional, List


class HealthResponse(BaseModel):
    """Health check response"""
    service: str
    status: str
    version: str
    supported_sources: Optional[List[str]] = None
