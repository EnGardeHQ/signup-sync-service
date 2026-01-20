"""
En Garde SignUp_Sync Microservice

Syncs funnel data from multiple sources (EasyAppointments, Zoom, Eventbrite, etc.)
to En Garde's database for marketing funnel tracking.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
import os

from app.services.funnel_sync_service import FunnelSyncService
from app.auth.verify import verify_service_token
from app.models.sync_request import (
    SyncRequest,
    SyncResponse,
    SyncStatusResponse,
    FunnelEventRequest,
    FunnelEventResponse,
    ConversionRequest,
    ConversionResponse
)
from app.models.health import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="En Garde SignUp_Sync Service",
    description="Multi-source funnel tracking and sync service",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - service info"""
    return {
        "service": "En Garde SignUp_Sync Service",
        "status": "running",
        "version": "2.0.0",
        "supported_sources": [
            "easyappointments",
            "zoom",
            "eventbrite",
            "poshvip",
            "manual",
            "referral",
            "direct_signup"
        ]
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Railway/deployment platforms"""
    return {
        "service": "signup-sync",
        "status": "healthy",
        "version": "2.0.0"
    }


# =====================================================
# FUNNEL SOURCE SYNC ENDPOINTS
# =====================================================

@app.post("/sync/easyappointments", response_model=SyncResponse)
async def sync_easyappointments(
    force_sync: bool = Query(False, description="Force re-sync even if up-to-date"),
    authorization: Optional[str] = Header(None)
):
    """
    Sync appointment bookers from EasyAppointments to funnel database.

    Fetches appointments from the last 7 days (configurable) and creates funnel events.
    """
    try:
        logger.info("EasyAppointments sync request received")

        # Verify service token
        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        # Perform sync
        sync_service = FunnelSyncService()
        result = await sync_service.sync_easyappointments(force_sync=force_sync)

        logger.info(f"EasyAppointments sync completed: {result['status']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"EasyAppointments sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.post("/sync/zoom", response_model=SyncResponse)
async def sync_zoom(
    force_sync: bool = Query(False),
    authorization: Optional[str] = Header(None)
):
    """
    Sync Zoom webinar/meeting registrants to funnel database.
    """
    try:
        logger.info("Zoom sync request received")

        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        result = await sync_service.sync_zoom(force_sync=force_sync)

        logger.info(f"Zoom sync completed: {result['status']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Zoom sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.post("/sync/eventbrite", response_model=SyncResponse)
async def sync_eventbrite(
    force_sync: bool = Query(False),
    authorization: Optional[str] = Header(None)
):
    """
    Sync Eventbrite event attendees to funnel database.
    """
    try:
        logger.info("Eventbrite sync request received")

        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        result = await sync_service.sync_eventbrite(force_sync=force_sync)

        logger.info(f"Eventbrite sync completed: {result['status']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Eventbrite sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.post("/sync/poshvip", response_model=SyncResponse)
async def sync_poshvip(
    force_sync: bool = Query(False),
    authorization: Optional[str] = Header(None)
):
    """
    Sync Posh.VIP contacts to funnel database.
    """
    try:
        logger.info("Posh.VIP sync request received")

        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        result = await sync_service.sync_poshvip(force_sync=force_sync)

        logger.info(f"Posh.VIP sync completed: {result['status']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Posh.VIP sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.post("/sync/all", response_model=dict)
async def sync_all_sources(
    force_sync: bool = Query(False),
    sources: Optional[List[str]] = Query(None, description="Specific sources to sync (default: all)"),
    authorization: Optional[str] = Header(None)
):
    """
    Sync all active funnel sources or specific sources.

    Args:
        force_sync: Force re-sync even if up-to-date
        sources: List of source types to sync (e.g., ["easyappointments", "zoom"])
                 If not provided, syncs all active sources.
    """
    try:
        logger.info(f"Multi-source sync request: {sources or 'all sources'}")

        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        results = await sync_service.sync_all_sources(
            force_sync=force_sync,
            source_types=sources
        )

        logger.info(f"Multi-source sync completed: {len(results)} sources")
        return {
            "status": "completed",
            "sources_synced": len(results),
            "results": results
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-source sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@app.get("/sync/status/{source_type}", response_model=SyncStatusResponse)
async def get_sync_status(
    source_type: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get sync status for a specific funnel source.

    Returns last sync time, next scheduled sync, and sync health.
    """
    try:
        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        status = await sync_service.get_sync_status(source_type)

        if not status:
            raise HTTPException(status_code=404, detail=f"Funnel source '{source_type}' not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync status for {source_type}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# =====================================================
# FUNNEL EVENT TRACKING ENDPOINTS
# =====================================================

@app.post("/funnel/event", response_model=FunnelEventResponse)
async def track_funnel_event(
    event: FunnelEventRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Track a funnel event from frontend or other services.

    Used for tracking user journey through the funnel (page views, form submissions, etc.)
    """
    try:
        logger.info(f"Funnel event received: {event.event_type} for {event.email}")

        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        result = await sync_service.track_funnel_event(event)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track funnel event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Event tracking failed: {str(e)}")


@app.post("/funnel/conversion", response_model=ConversionResponse)
async def mark_conversion(
    conversion: ConversionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Mark a lead as converted to platform user.

    Creates a FunnelConversion record linking funnel events to user signup.
    """
    try:
        logger.info(f"Conversion request for email: {conversion.email}")

        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        result = await sync_service.mark_conversion(conversion)

        logger.info(f"Conversion recorded: {result['conversion_id']}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark conversion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Conversion tracking failed: {str(e)}")


# =====================================================
# ANALYTICS ENDPOINTS
# =====================================================

@app.get("/analytics/funnel-metrics")
async def get_funnel_metrics(
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    authorization: Optional[str] = Header(None)
):
    """
    Get aggregated funnel metrics.

    Returns conversion rates, lead counts, and funnel performance by source.
    """
    try:
        if not verify_service_token(authorization):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

        sync_service = FunnelSyncService()
        metrics = await sync_service.get_funnel_metrics(
            source_type=source_type,
            start_date=start_date,
            end_date=end_date
        )

        return metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get funnel metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
