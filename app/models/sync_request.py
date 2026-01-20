"""
Request and Response Models for SignUp_Sync Service
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =====================================================
# SYNC REQUEST/RESPONSE MODELS
# =====================================================

class SyncRequest(BaseModel):
    """Request to trigger a funnel sync"""
    force_sync: bool = False
    sync_window_days: Optional[int] = 7  # How many days back to sync


class SyncResponse(BaseModel):
    """Response from sync operation"""
    status: str  # success, failed, partial
    source_type: str
    source_name: str

    # Counts
    leads_processed: int
    leads_created: int
    leads_updated: int
    leads_skipped: int
    errors_count: int

    # Timing
    started_at: datetime
    completed_at: datetime
    duration_seconds: int

    # Details
    sync_log_id: str
    error_messages: Optional[List[str]] = None
    summary: str


class SyncStatusResponse(BaseModel):
    """Status of a funnel source sync"""
    source_id: str
    source_type: str
    source_name: str
    is_active: bool
    auto_sync_enabled: bool

    # Sync timing
    last_sync_at: Optional[datetime]
    last_sync_status: Optional[str]
    last_sync_message: Optional[str]
    next_sync_at: Optional[datetime]
    sync_frequency_hours: int

    # Stats
    total_leads_captured: int
    total_conversions: int

    # Health
    health_status: str  # healthy, warning, error


# =====================================================
# FUNNEL EVENT MODELS
# =====================================================

class FunnelEventRequest(BaseModel):
    """Request to track a funnel event"""
    # Source
    source_type: str  # easyappointments, zoom, eventbrite, etc.
    external_id: Optional[str] = None  # ID in source system

    # Event
    event_type: str  # lead_captured, appointment_booked, etc.
    event_timestamp: Optional[datetime] = None  # Defaults to now

    # Lead info
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

    # UTM tracking
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None

    # Context
    referrer: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Event-specific data
    event_data: Optional[Dict[str, Any]] = None
    external_metadata: Optional[Dict[str, Any]] = None


class FunnelEventResponse(BaseModel):
    """Response from tracking a funnel event"""
    success: bool
    event_id: str
    event_type: str
    email: Optional[str]
    created_at: datetime
    message: str


# =====================================================
# CONVERSION MODELS
# =====================================================

class ConversionRequest(BaseModel):
    """Request to mark a lead as converted"""
    email: EmailStr
    user_id: str  # UUID of the newly created user

    # Optional conversion details
    converted_at: Optional[datetime] = None  # Defaults to now
    estimated_value_usd: Optional[int] = None  # Based on subscription tier


class ConversionResponse(BaseModel):
    """Response from conversion tracking"""
    success: bool
    conversion_id: str
    user_id: str
    email: str

    # Attribution
    first_touch_source_type: str
    first_touch_at: datetime
    last_touch_source_type: str
    last_touch_at: datetime

    # Metrics
    days_to_conversion: int
    total_touchpoints: int

    message: str


# =====================================================
# HEALTH CHECK MODEL
# =====================================================

class HealthResponse(BaseModel):
    """Health check response"""
    service: str
    status: str
    version: str
    supported_sources: Optional[List[str]] = None
