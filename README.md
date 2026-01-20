# En Garde SignUp_Sync Service

Multi-source funnel tracking and synchronization microservice for En Garde.

## Overview

SignUp_Sync is a dedicated microservice that syncs marketing funnel data from multiple sources (EasyAppointments, Zoom, Eventbrite, Posh.VIP, etc.) into En Garde's database for comprehensive funnel tracking and conversion analytics.

## Features

- **Multi-Source Support**: EasyAppointments, Zoom, Eventbrite, Posh.VIP, Manual, Referrals, Direct Signups
- **Automatic & Manual Sync**: Scheduled daily sync + on-demand triggers
- **Comprehensive Event Tracking**: 11 event types from lead capture to conversion
- **Attribution Tracking**: First-touch and last-touch attribution with UTM parameters
- **Conversion Analytics**: Full funnel metrics and conversion rate tracking
- **RESTful API**: Clean API for integration with En Garde backend

## Architecture

```
signup-sync-service/
├── app/
│   ├── main.py                    # FastAPI application
│   ├── models/
│   │   ├── sync_request.py        # Request/response models
│   │   └── health.py              # Health check models
│   ├── services/
│   │   └── funnel_sync_service.py # Core sync logic
│   ├── database/
│   │   └── connection.py          # Database connection
│   └── auth/
│       └── verify.py              # Service token auth
├── requirements.txt
├── Dockerfile
├── railway.json
└── README.md
```

## API Endpoints

### Sync Endpoints
- `POST /sync/easyappointments` - Sync EasyAppointments bookers
- `POST /sync/zoom` - Sync Zoom registrants
- `POST /sync/eventbrite` - Sync Eventbrite attendees
- `POST /sync/poshvip` - Sync Posh.VIP contacts
- `POST /sync/all` - Sync all active sources
- `GET /sync/status/{source_type}` - Get sync status

### Event Tracking
- `POST /funnel/event` - Track individual funnel event
- `POST /funnel/conversion` - Mark lead as converted

### Analytics
- `GET /analytics/funnel-metrics` - Get funnel performance metrics

### Health
- `GET /` - Service info
- `GET /health` - Health check

## Environment Variables

```bash
# Database
ENGARDE_DATABASE_URL=postgresql://user:password@host:port/database

# Service Authentication
SIGNUP_SYNC_SERVICE_TOKEN=your-secure-random-token

# CORS (optional)
CORS_ORIGINS=https://app.engarde.media,https://admin.engarde.media
```

## Deployment

### Railway (Recommended)

1. **Create Railway Project**
   ```bash
   railway link
   ```

2. **Set Environment Variables**
   ```bash
   railway variables set ENGARDE_DATABASE_URL=$DATABASE_PUBLIC_URL
   railway variables set SIGNUP_SYNC_SERVICE_TOKEN=$(openssl rand -hex 32)
   ```

3. **Deploy**
   ```bash
   railway up
   ```

### Docker

1. **Build Image**
   ```bash
   docker build -t signup-sync-service .
   ```

2. **Run Container**
   ```bash
   docker run -p 8001:8001 \
     -e ENGARDE_DATABASE_URL=$DATABASE_URL \
     -e SIGNUP_SYNC_SERVICE_TOKEN=$TOKEN \
     signup-sync-service
   ```

## Development

### Local Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export ENGARDE_DATABASE_URL="postgresql://localhost/engarde"
   export SIGNUP_SYNC_SERVICE_TOKEN="dev_token"
   ```

3. **Run Server**
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

4. **Test**
   ```bash
   curl http://localhost:8001/health
   ```

### Running Tests

```bash
# Test sync endpoint
curl -X POST http://localhost:8001/sync/easyappointments \
  -H "Authorization: Bearer $SIGNUP_SYNC_SERVICE_TOKEN"

# Track test event
curl -X POST http://localhost:8001/funnel/event \
  -H "Authorization: Bearer $SIGNUP_SYNC_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "easyappointments",
    "event_type": "appointment_booked",
    "email": "test@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

## Database Schema

The service requires these tables in the En Garde database:

- `funnel_sources` - Funnel source configurations
- `funnel_events` - Individual funnel events
- `funnel_conversions` - Conversion tracking
- `funnel_sync_logs` - Sync operation logs

See `/Users/cope/EnGardeHQ/production-backend/app/models/funnel_models.py` for schema.

## Security

### Authentication
All endpoints require a Bearer token:
```
Authorization: Bearer your-service-token
```

### Token Generation
Generate a secure random token:
```bash
openssl rand -hex 32
```

### Best Practices
- Rotate tokens quarterly
- Use different tokens for dev/staging/production
- Never commit tokens to git
- Store tokens in environment variables only

## Monitoring

### Health Checks
- Railway: Automatic health checks on `/health`
- Manual: `curl https://your-service.railway.app/health`

### Key Metrics
- Sync success rate
- Event tracking volume
- API response times
- Database connection pool

## Troubleshooting

### Service can't connect to database
- Verify `ENGARDE_DATABASE_URL` is correct
- Check if database accepts external connections
- Ensure connection string includes proper credentials

### Sync returning 0 results
- Check `funnel_sources` table has active sources
- Verify source API credentials are valid
- Check sync logs in `funnel_sync_logs` table

### 401 Unauthorized errors
- Verify `SIGNUP_SYNC_SERVICE_TOKEN` matches between services
- Check Authorization header format: `Bearer <token>`

## License

Proprietary - En Garde Platform

## Support

For questions or issues, contact the En Garde platform team.
