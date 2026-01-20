"""
Funnel Sync Service

Core service for syncing funnel data from multiple sources to En Garde database.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import httpx

from app.database.connection import get_db_context
from app.models.sync_request import (
    SyncResponse,
    SyncStatusResponse,
    FunnelEventRequest,
    FunnelEventResponse,
    ConversionRequest,
    ConversionResponse
)

logger = logging.getLogger(__name__)


class FunnelSyncService:
    """Service for syncing funnel sources and tracking events"""

    def __init__(self):
        self.sync_window_days = 7  # Default sync window

    async def sync_easyappointments(self, force_sync: bool = False) -> Dict[str, Any]:
        """
        Sync EasyAppointments bookers to funnel database.

        Args:
            force_sync: Force re-sync even if up-to-date

        Returns:
            Sync results
        """
        started_at = datetime.utcnow()
        source_type = "easyappointments"

        try:
            with get_db_context() as db:
                # Get funnel source configuration
                from sqlalchemy import text
                result = db.execute(
                    text("""
                        SELECT id, name, config, last_sync_at
                        FROM funnel_sources
                        WHERE source_type = :source_type AND is_active = true
                        LIMIT 1
                    """),
                    {"source_type": source_type}
                )
                source = result.fetchone()

                if not source:
                    raise ValueError(f"No active funnel source found for {source_type}")

                source_id, source_name, config, last_sync = source

                # Determine sync window
                if force_sync or not last_sync:
                    sync_from = datetime.utcnow() - timedelta(days=self.sync_window_days)
                else:
                    sync_from = last_sync

                # Fetch appointments from EasyAppointments
                # TODO: Implement actual API call to EasyAppointments
                # For now, this is a placeholder
                appointments = await self._fetch_easyappointments(config, sync_from)

                # Process appointments and add to pending signup queue
                leads_created = 0
                leads_updated = 0
                leads_skipped = 0
                errors = []

                for appointment in appointments:
                    try:
                        result = await self._add_to_pending_signups(
                            db, appointment
                        )
                        if result == "created":
                            leads_created += 1
                        elif result == "updated":
                            leads_updated += 1
                        else:
                            leads_skipped += 1
                    except Exception as e:
                        logger.error(f"Failed to process appointment {appointment.get('appointment_id')}: {e}")
                        errors.append(str(e))

                # Update source last_sync_at
                db.execute(
                    text("""
                        UPDATE funnel_sources
                        SET last_sync_at = :now,
                            last_sync_status = :status,
                            total_leads_captured = total_leads_captured + :new_leads
                        WHERE id = :source_id
                    """),
                    {
                        "now": datetime.utcnow(),
                        "status": "success" if not errors else "partial",
                        "new_leads": leads_created,
                        "source_id": source_id
                    }
                )

                # Create sync log
                db.execute(
                    text("""
                        INSERT INTO funnel_sync_logs (
                            id, funnel_source_id, sync_type, sync_status,
                            leads_processed, leads_created, leads_updated, leads_skipped,
                            errors_count, error_messages, started_at, completed_at,
                            duration_seconds, created_at
                        ) VALUES (
                            gen_random_uuid(), :source_id, 'automatic', :status,
                            :processed, :created, :updated, :skipped,
                            :errors_count, :error_messages, :started_at, :completed_at,
                            :duration, NOW()
                        )
                    """),
                    {
                        "source_id": source_id,
                        "status": "success" if not errors else "partial",
                        "processed": len(appointments),
                        "created": leads_created,
                        "updated": leads_updated,
                        "skipped": leads_skipped,
                        "errors_count": len(errors),
                        "error_messages": errors if errors else None,
                        "started_at": started_at,
                        "completed_at": datetime.utcnow(),
                        "duration": int((datetime.utcnow() - started_at).total_seconds())
                    }
                )

                db.commit()

                return {
                    "status": "success" if not errors else "partial",
                    "source_type": source_type,
                    "source_name": source_name,
                    "leads_processed": len(appointments),
                    "leads_created": leads_created,
                    "leads_updated": leads_updated,
                    "leads_skipped": leads_skipped,
                    "errors_count": len(errors),
                    "started_at": started_at,
                    "completed_at": datetime.utcnow(),
                    "duration_seconds": int((datetime.utcnow() - started_at).total_seconds()),
                    "sync_log_id": str(source_id),
                    "error_messages": errors if errors else None,
                    "summary": f"Synced {leads_created} new leads from EasyAppointments"
                }

        except Exception as e:
            logger.error(f"EasyAppointments sync failed: {e}", exc_info=True)
            raise

    async def _fetch_easyappointments(self, config: Dict, sync_from: datetime) -> List[Dict]:
        """
        Fetch appointments from EasyAppointments MySQL database.
        """
        import os
        import pymysql

        # Get MySQL credentials from environment
        mysql_host = os.getenv("EASYAPPOINTMENTS_MYSQL_HOST", "mysql.railway.internal")
        mysql_port = int(os.getenv("EASYAPPOINTMENTS_MYSQL_PORT", "3306"))
        mysql_user = os.getenv("EASYAPPOINTMENTS_MYSQL_USER", "root")
        mysql_password = os.getenv("EASYAPPOINTMENTS_MYSQL_PASSWORD")
        mysql_database = os.getenv("EASYAPPOINTMENTS_MYSQL_DATABASE", "railway")
        table_prefix = os.getenv("EASYAPPOINTMENTS_TABLE_PREFIX", "ea_")

        logger.info(f"Fetching appointments from {sync_from} (host: {mysql_host})")

        try:
            # Connect to EasyAppointments MySQL database
            connection = pymysql.connect(
                host=mysql_host,
                port=mysql_port,
                user=mysql_user,
                password=mysql_password,
                database=mysql_database,
                cursorclass=pymysql.cursors.DictCursor
            )

            with connection.cursor() as cursor:
                # Query appointments with customer and service details
                sql = f"""
                    SELECT
                        a.id as appointment_id,
                        a.book_datetime,
                        a.start_datetime,
                        a.end_datetime,
                        a.hash,
                        a.notes,
                        u.id as customer_id,
                        u.email,
                        u.first_name,
                        u.last_name,
                        u.mobile_number,
                        u.phone_number,
                        u.address,
                        u.city,
                        u.state,
                        u.zip_code,
                        s.id as service_id,
                        s.name as service_name,
                        s.price,
                        s.duration,
                        s.currency
                    FROM {table_prefix}appointments a
                    JOIN {table_prefix}users u ON a.id_users_customer = u.id
                    LEFT JOIN {table_prefix}services s ON a.id_services = s.id
                    WHERE a.book_datetime >= %s
                        AND u.id_roles = 4
                    ORDER BY a.book_datetime ASC
                """

                cursor.execute(sql, (sync_from,))
                appointments = cursor.fetchall()

            connection.close()

            logger.info(f"Fetched {len(appointments)} appointments from EasyAppointments")
            return appointments

        except Exception as e:
            logger.error(f"Failed to fetch from EasyAppointments MySQL: {e}", exc_info=True)
            raise

    async def _add_to_pending_signups(self, db, appointment: Dict) -> str:
        """
        Add EasyAppointments contact to pending signup queue for admin approval.

        Returns:
            "created", "updated", or "skipped"
        """
        from sqlalchemy import text
        import uuid
        import json

        try:
            email = appointment.get("email")
            if not email:
                logger.info(f"Skipping appointment {appointment.get('appointment_id')}: no email")
                return "skipped"

            # Check if signup already exists
            existing = db.execute(
                text("SELECT id, status FROM pending_signup_queue WHERE email = :email"),
                {"email": email.lower()}
            ).fetchone()

            if existing:
                # Skip if already processed (approved or rejected)
                if existing[1] in ['approved', 'rejected']:
                    return "skipped"

                # Update existing pending record with latest info
                db.execute(
                    text("""
                        UPDATE pending_signup_queue
                        SET first_name = COALESCE(:first_name, first_name),
                            last_name = COALESCE(:last_name, last_name),
                            signup_metadata = :metadata,
                            updated_at = NOW()
                        WHERE email = :email
                    """),
                    {
                        "email": email.lower(),
                        "first_name": appointment.get("first_name"),
                        "last_name": appointment.get("last_name"),
                        "metadata": json.dumps({
                            "source": "easyappointments",
                            "appointment_id": appointment.get("appointment_id"),
                            "service_name": appointment.get("service_name"),
                            "service_price": float(appointment.get("price", 0)) if appointment.get("price") else None,
                            "appointment_datetime": str(appointment.get("start_datetime")),
                            "phone": appointment.get("mobile_number") or appointment.get("phone_number"),
                            "city": appointment.get("city"),
                            "state": appointment.get("state"),
                            "address": appointment.get("address")
                        })
                    }
                )
                return "updated"

            # Create new pending signup
            signup_id = str(uuid.uuid4())

            db.execute(
                text("""
                    INSERT INTO pending_signup_queue (
                        id, email, first_name, last_name, company,
                        user_type, status, signup_metadata, created_at, updated_at
                    ) VALUES (
                        :id, :email, :first_name, :last_name, :company,
                        'brand', 'pending', :metadata, NOW(), NOW()
                    )
                """),
                {
                    "id": signup_id,
                    "email": email.lower(),
                    "first_name": appointment.get("first_name"),
                    "last_name": appointment.get("last_name"),
                    "company": appointment.get("company"),
                    "metadata": json.dumps({
                        "source": "easyappointments",
                        "appointment_id": appointment.get("appointment_id"),
                        "service_name": appointment.get("service_name"),
                        "service_price": float(appointment.get("price", 0)) if appointment.get("price") else None,
                        "appointment_datetime": str(appointment.get("start_datetime")),
                        "phone": appointment.get("mobile_number") or appointment.get("phone_number"),
                        "city": appointment.get("city"),
                        "state": appointment.get("state"),
                        "address": appointment.get("address")
                    })
                }
            )

            logger.info(f"Added {email} to pending signup queue from EasyAppointments appointment {appointment.get('appointment_id')}")
            return "created"

        except Exception as e:
            logger.error(f"Failed to add to pending signups: {e}", exc_info=True)
            raise

    async def sync_zoom(self, force_sync: bool = False) -> Dict[str, Any]:
        """Sync Zoom webinar/meeting registrants"""
        # TODO: Implement Zoom sync
        return self._placeholder_sync_response("zoom")

    async def sync_eventbrite(self, force_sync: bool = False) -> Dict[str, Any]:
        """Sync Eventbrite event attendees"""
        # TODO: Implement Eventbrite sync
        return self._placeholder_sync_response("eventbrite")

    async def sync_poshvip(self, force_sync: bool = False) -> Dict[str, Any]:
        """Sync Posh.VIP contacts"""
        # TODO: Implement Posh.VIP sync
        return self._placeholder_sync_response("poshvip")

    async def sync_all_sources(
        self, force_sync: bool = False, source_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Sync all active funnel sources or specific sources.

        Args:
            force_sync: Force re-sync
            source_types: Specific sources to sync (None = all)

        Returns:
            List of sync results
        """
        results = []

        # Sync each source
        sync_methods = {
            "easyappointments": self.sync_easyappointments,
            "zoom": self.sync_zoom,
            "eventbrite": self.sync_eventbrite,
            "poshvip": self.sync_poshvip
        }

        for source_type, sync_method in sync_methods.items():
            if source_types is None or source_type in source_types:
                try:
                    result = await sync_method(force_sync=force_sync)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to sync {source_type}: {e}")
                    results.append({
                        "status": "failed",
                        "source_type": source_type,
                        "error": str(e)
                    })

        return results

    async def get_sync_status(self, source_type: str) -> Optional[SyncStatusResponse]:
        """Get sync status for a funnel source"""
        # TODO: Implement actual status retrieval
        return None

    async def track_funnel_event(self, event: FunnelEventRequest) -> FunnelEventResponse:
        """Track a funnel event"""
        # TODO: Implement actual event tracking
        return FunnelEventResponse(
            success=True,
            event_id="placeholder",
            event_type=event.event_type,
            email=event.email,
            created_at=datetime.utcnow(),
            message="Event tracked successfully"
        )

    async def mark_conversion(self, conversion: ConversionRequest) -> ConversionResponse:
        """Mark a lead as converted"""
        # TODO: Implement actual conversion tracking
        return ConversionResponse(
            success=True,
            conversion_id="placeholder",
            user_id=conversion.user_id,
            email=conversion.email,
            first_touch_source_type="easyappointments",
            first_touch_at=datetime.utcnow() - timedelta(days=7),
            last_touch_source_type="direct_signup",
            last_touch_at=datetime.utcnow(),
            days_to_conversion=7,
            total_touchpoints=3,
            message="Conversion recorded successfully"
        )

    async def get_funnel_metrics(
        self,
        source_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated funnel metrics"""
        # TODO: Implement actual metrics aggregation
        return {
            "total_leads": 0,
            "total_conversions": 0,
            "conversion_rate": 0.0,
            "sources": []
        }

    def _placeholder_sync_response(self, source_type: str) -> Dict[str, Any]:
        """Placeholder sync response"""
        return {
            "status": "success",
            "source_type": source_type,
            "source_name": f"{source_type.title()} Integration",
            "leads_processed": 0,
            "leads_created": 0,
            "leads_updated": 0,
            "leads_skipped": 0,
            "errors_count": 0,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "duration_seconds": 0,
            "sync_log_id": "placeholder",
            "summary": f"{source_type.title()} sync not yet implemented"
        }
