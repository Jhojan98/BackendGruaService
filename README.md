# Terra Towing Dispatch - Backend Services

A FastAPI-based microservices architecture for the Terra Towing Dispatch system, providing RESTful APIs for fleet management, trip dispatching, client management, and media handling.

## 🚀 Quick Start

**Prerequisites:** Docker and Docker Compose

1. **Start all services:**
   ```bash
   docker compose up --build
   ```

2. **Access API documentation:**
   - Gateway: http://localhost:8000/docs
   - Auth Service: http://localhost:8001/docs
   - Dispatch Service: http://localhost:8002/docs
   - Fleet Service: http://localhost:8003/docs
   - Clients Service: http://localhost:8004/docs
   - Media Service: http://localhost:8005/docs

3. **Run tests:**
   ```bash
   pip install -r tests/requirements-test.txt
   pytest
   ```

---

## 🏗️ Architecture Overview

### Microservices Pattern

The backend follows a **microservices architecture** with an **API Gateway pattern**:

```
┌─────────────────┐
│   Frontend App  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API Gateway   │  (Port 8000)
│  /api/v1/*      │
└────────┬────────┘
         │
    ┌────┴────┬────────────┬──────────┐
    ▼         ▼            ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  Auth  │ │Dispatch│ │ Fleet  │ │Clients │
│ :8001  │ │ :8002  │ │ :8003  │ │ :8004  │
└────────┘ └────────┘ └────────┘ └────────┘
```

### Tech Stack

- **FastAPI** - High-performance Python web framework
- **PostgreSQL 16** - Relational database with service-level isolation
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation and serialization
- **HTTPX** - Async HTTP client for inter-service communication
- **python-jose** - JWT token handling
- **Docker Compose** - Container orchestration
- **Cloudflare R2** - Object storage for media assets

### Project Structure

```
BackendGruaService/
├── gateway/                    # API Gateway (main entrypoint)
│   ├── app/
│   │   ├── main.py            # Route definitions and request forwarding
│   │   └── config.py          # Gateway configuration
│   ├── Dockerfile
│   └── requirements.txt
├── services/
│   ├── auth-service/          # Authentication & user management (:8001)
│   ├── dispatch-service/      # Trip lifecycle (:8002)
│   ├── fleet-service/         # Fleet inventory & GPS (:8003)
│   ├── clients-service/       # Client registry (:8004)
│   ├── media-service/         # Image uploads to R2 (:8005)
│   ├── drivers-service/       # Driver management
│   └── settings-service/      # Settings & billing configuration
├── infra/
│   └── postgres/
│       └── init/              # Database initialization scripts
├── seed-data/
│   └── initial_data.json      # Initial seed data for all services
├── tests/                     # Integration tests
├── docker-compose.yml         # Service orchestration
└── .env                       # Environment configuration
```

---

## 🔧 How It Works

### 1. API Gateway (Port 8000)

The gateway is the **single entry point** for all frontend requests. It handles:

- **Route Aggregation**: Forwards requests to appropriate microservices
- **JWT Authentication**: Validates tokens on protected endpoints
- **Role-Based Access Control**: Enforces admin/dispatcher permissions
- **Request Transformation**: Normalizes payloads between services
- **Cross-Cutting Concerns**: CORS, error handling, payload validation

**Request Flow:**
1. Frontend sends request to `/api/v1/trips`
2. Gateway validates JWT token from `Authorization` header
3. Gateway forwards to `dispatch-service:8002/internal/trips`
4. Response is returned to frontend

**Smart Features:**
- **Multipart Form Handling**: Gateway can accept file uploads and forward to media-service
- **Payload Normalization**: Converts camelCase (frontend) to snake_case (services)
- **Error Translation**: Converts upstream errors to proper HTTP status codes

### 2. Authentication Service (Port 8001)

**Purpose:** User authentication, profile management, and preferences

**Key Features:**
- JWT token generation on login
- User profile CRUD with preferences (theme, language, notifications)
- Profile image URL tracking
- Role-based access (admin vs dispatcher)

**Database:** `auth_db`
**Tables:** `users`

**User Model Fields:**
- `id`, `email`, `full_name`, `role`, `password_hash`
- `profile_image_url` - Link to media asset
- `theme` - light/dark mode preference
- `language` - i18n preference
- `email_alerts`, `sms_urgent_alerts`, `browser_notifications` - Notification settings
- `employee_id`, `office_location` - Additional profile data

### 3. Dispatch Service (Port 8002)

**Purpose:** Complete trip lifecycle management

**Key Features:**
- Create new towing trips
- Track trip status (Pending, Dispatched, En Route, In Progress, Completed)
- Assign tow trucks to trips
- Trip history and filtering

**Database:** `dispatch_db`
**Tables:** `trips`

**Trip Model Fields:**
- `id`, `client_id`, `client_name`
- `origin`, `destination`, `distance`
- `status` - Current trip status
- `tow_truck` - Assigned unit
- `date`, `time` - Scheduling information

**Trip Status Flow:**
```
Pending → Dispatched → En Route → In Progress → Completed
```

### 4. Fleet Service (Port 8003)

**Purpose:** Tow truck inventory and real-time GPS tracking

**Key Features:**
- Fleet registry with truck details
- Real-time location tracking via **WebSocket**
- Status management (Available, On Trip, Maintenance, Offline)

**Database:** `fleet_db`
**Tables:** `trucks`

**Truck Model Fields:**
- `id`, `unit_number`, `truck_type`
- `status` - Current operational status
- `lat`, `lng` - GPS coordinates

**WebSocket Stream:**
- `ws://localhost:8003/ws/locations` - Real-time location updates
- Frontend subscribes to this for live map updates

### 5. Clients Service (Port 8004)

**Purpose:** Corporate and individual client management

**Key Features:**
- Client registry with contact information
- Membership tiers and status tracking
- Service history with revenue tracking
- Client logo uploads via media-service integration

**Database:** `clients_db`
**Tables:** `clients`, `client_history`

**Client Model Fields:**
- `id`, `name`, `membership`, `phone`
- `status`, `contact_person`, `email`, `client_type`
- `logo_url` - Link to media asset
- `last_service_date`

**Client History Fields:**
- `id`, `client_id`, `service_date`, `description`, `revenue`

### 6. Media Service (Port 8005)

**Purpose:** Image upload and storage via Cloudflare R2

**Key Features:**
- Upload images to Cloudflare R2 (S3-compatible)
- Metadata registry for all media assets
- Public and signed URL access control
- Entity association (clients, users, trips, etc.)

**Database:** `media_db`
**Tables:** `media_assets`

**Media Asset Fields:**
- `id`, `entity_type`, `entity_id` - Links to other services
- `original_filename`, `mime_type`, `file_size_bytes`
- `r2_key` - R2 storage path
- `url` - Public or signed URL
- `access_mode` - public/signed
- `uploaded_by`, `created_at`, `updated_at`

**Supported Formats:** JPEG, PNG, WebP
**Max Upload Size:** 10 MB

**Access Control:**
- **Public entities:** `clients`, `users` - Direct public URLs
- **Signed entities:** `trips`, `dispatch` - Time-limited signed URLs (1 hour default)

### 7. Drivers Service

**Purpose:** Driver roster and performance tracking

Manages driver profiles, shift assignments, unit allocations, and performance metrics.

### 8. Settings Service

**Purpose:** System configuration and billing administration

Handles tariff configuration, billing settings, and system-wide preferences.

---

## 💾 Database Architecture

### Database Isolation

Each microservice has its **own dedicated database**, ensuring:
- Service autonomy
- Independent scaling
- Failure isolation
- Clear ownership boundaries

**Database Creation:**
```
infra/postgres/init/01-create-databases.sql
```

**Databases:**
- `auth_db` - User accounts and preferences
- `dispatch_db` - Trip records
- `fleet_db` - Truck inventory and GPS
- `clients_db` - Client registry and history
- `media_db` - Media asset metadata

### Schema Management

- **Table Creation:** Each service runs `Base.metadata.create_all()` on startup
- **Schema Definitions:** Located in `app/models.py` within each service
- **Migrations:** Handled by service restart (development); production should use Alembic

### Seed Data

**Location:** `seed-data/initial_data.json`

**How It Works:**
1. Services check if their tables are empty on startup
2. If empty, insert records from `initial_data.json`
3. If data exists, skip seeding (preserves existing data)

**Reset and Reseed:**
```bash
docker compose down -v  # Destroys all volumes
docker compose up --build
```

---

## 🔐 Security Model

### JWT Authentication

**Token Generation:**
- User logs in via `POST /api/v1/auth/login`
- Auth service returns JWT with `sub` (user ID), `email`, `role`
- Token expiration: 120 minutes (configurable)

**Token Validation:**
- Gateway extracts Bearer token from `Authorization` header
- Validates signature using `JWT_SECRET`
- Decodes payload and passes user context to routes

**Role-Based Access:**
- **Admin:** Full access to all endpoints, including user management
- **Dispatcher:** Access to operational endpoints (trips, fleet, clients)

### Protected Endpoints

All endpoints under `/api/v1/*` require authentication except:
- `POST /api/v1/auth/login` - Public

**Admin-Only Endpoints:**
- `GET /api/v1/users` - List all users
- `POST /api/v1/users` - Create user
- `PATCH /api/v1/users/{id}` - Update any user
- `POST /api/v1/clients` - Create client
- `PATCH /api/v1/clients/{id}` - Update client

### CORS

CORS is enabled for all origins in development:
```python
allow_origins=["*"]
```

**Production Recommendation:** Restrict to specific frontend domain

---

## 🔄 Inter-Service Communication

### Gateway-to-Service Pattern

The gateway acts as a **reverse proxy**, forwarding requests to internal services:

```python
# Example: Gateway forwards trip creation
POST /api/v1/trips  →  POST http://dispatch-service:8002/internal/trips
```

**Service URLs configured in:**
- `.env` file
- Gateway `Settings` class reads environment variables

### HTTP Client

- **Library:** HTTPX (async HTTP client)
- **Timeout:** 20 seconds for JSON, 30 seconds for file uploads
- **Error Handling:** Translates upstream errors to HTTPException

### File Upload Flow

For profile images and client logos:

1. Frontend sends `multipart/form-data` to gateway
2. Gateway extracts file and forwards to media-service
3. Media-service uploads to Cloudflare R2
4. Media-service returns URL
5. Gateway stores URL in target entity's record

---

## 📡 API Endpoints

### Gateway Routes (`/api/v1`)

#### Authentication
- `POST /auth/login` - User login, returns JWT

#### User Management
- `GET /users/me` - Current user profile
- `PATCH /users/me` - Update own profile (supports file upload)
- `GET /users` - List all users (admin only)
- `POST /users` - Create user (admin only)
- `PATCH /users/{id}` - Update any user (admin only)

#### Dashboard
- `GET /dashboard/stats` - KPI metrics
- `GET /dashboard/quick-actions` - Dynamic action items

#### Trips & Dispatch
- `GET /trips` - List trips (filterable by `status`, `date`)
- `GET /trips/{id}` - Trip details
- `POST /trips` - Create new trip
- `PUT /trips/{id}/status` - Update trip status
- `PUT /trips/{id}/assign` - Assign tow truck to trip

#### Fleet
- `GET /fleet` - List all trucks
- `GET /fleet/{id}` - Truck details
- `GET /fleet/locations` - Real-time GPS coordinates

#### Clients
- `GET /clients` - List all clients
- `POST /clients` - Create client (admin only, supports logo upload)
- `GET /clients/{id}/history` - Client service history
- `PATCH /clients/{id}` - Update client (admin only, supports logo upload)

#### Media
- `POST /media/upload` - Upload image (internal route)
- `GET /media/{id}` - Get media asset details
- `GET /media/by-entity` - Get media by entity type and ID

#### Analytics
- `GET /analytics/revenue` - Revenue time-series data
- `GET /analytics/performance` - KPI metrics (ETA, trip duration, completion rates)

#### Notifications
- `GET /notifications` - User notifications

#### Health
- `GET /api/health` - Gateway health check

### Service-Level Endpoints

Each service exposes internal routes at `/internal/*` for gateway consumption:

- **Auth Service:** `/internal/auth/login`, `/internal/users/*`
- **Dispatch Service:** `/internal/trips/*`
- **Fleet Service:** `/internal/fleet/*`, `/internal/fleet/locations`
- **Clients Service:** `/internal/clients/*`
- **Media Service:** `/internal/media/upload`, `/internal/media/*`

### WebSocket

- `ws://localhost:8003/ws/locations` - Real-time fleet GPS stream

---

## 🛠️ Development

### Service Structure

Each microservice follows a consistent structure:

```
service-name/
├── app/
│   ├── config.py       # Environment configuration
│   ├── database.py     # SQLAlchemy engine/session/base
│   ├── models.py       # Database schema (table classes)
│   ├── schemas.py      # Request/response DTOs (Pydantic)
│   ├── service.py      # Business logic
│   └── main.py         # API routes (thin controller)
├── Dockerfile
└── requirements.txt
```

### Environment Configuration

**Main `.env` file:**
```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# JWT
JWT_SECRET=change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120

# Service Ports
AUTH_SERVICE_PORT=8001
DISPATCH_SERVICE_PORT=8002
FLEET_SERVICE_PORT=8003
CLIENTS_SERVICE_PORT=8004
MEDIA_SERVICE_PORT=8005
GATEWAY_PORT=8000

# Cloudflare R2
R2_ENDPOINT_URL=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=grua-media
R2_PUBLIC_BASE_URL=https://pub-xxx.r2.dev

# Media Settings
MAX_UPLOAD_SIZE_MB=10
ALLOWED_IMAGE_MIME_TYPES=image/jpeg,image/png,image/webp
PUBLIC_ENTITY_TYPES=clients,users
SIGNED_ENTITY_TYPES=trips,dispatch
```

### Available Docker Commands

```bash
docker compose up              # Start all services
docker compose up --build      # Rebuild and start
docker compose down            # Stop services
docker compose down -v         # Stop and delete volumes
docker compose logs -f         # Follow logs
docker compose logs auth-service  # Service-specific logs
```

### API Documentation

FastAPI auto-generates interactive API docs (Swagger UI) at:
- `http://localhost:{port}/docs` - Swagger UI
- `http://localhost:{port}/redoc` - ReDoc

---

## 🧪 Testing

Integration tests validate the entire system through the gateway:

**Install test dependencies:**
```bash
pip install -r tests/requirements-test.txt
```

**Run tests:**
```bash
pytest
```

**Custom gateway URL:**
```bash
API_BASE_URL=http://localhost:8000 pytest
```

**Test Configuration:**
- `pytest.ini` - Pytest configuration
- Tests target the running gateway, not individual services

---

## 👤 Default Users

### Admin Account
- **Email:** `admin@terra.local`
- **Password:** `admin123`

### Dispatcher Account
- **Email:** `dispatcher@terra.local`
- **Password:** `dispatch123`

**Login Example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@terra.local", "password": "admin123"}'
```

Returns JWT token for subsequent requests.

---

## 🚀 Deployment Considerations

### Production Checklist

1. **Security:**
   - Change `JWT_SECRET` to a strong random value
   - Restrict CORS to specific domains
   - Use strong database passwords
   - Enable HTTPS for all services

2. **Infrastructure:**
   - Use reverse proxy (Nginx, Traefik) for SSL termination
   - Implement service mesh for inter-service communication
   - Set up database backups
   - Configure health checks and monitoring

3. **Scaling:**
   - Each service can scale independently
   - Use connection pooling for PostgreSQL
   - Consider read replicas for analytics

4. **Media Storage:**
   - Configure Cloudflare R2 with proper access policies
   - Set up CDN for public assets
   - Implement lifecycle policies for old media

5. **Monitoring:**
   - Add structured logging
   - Implement distributed tracing
   - Set up alerting for service failures
   - Monitor database performance

---

## 📊 Current Implementation Status

### Fully Implemented ✅
- Authentication & JWT
- User management (CRUD, profile images)
- Trip lifecycle (create, assign, status updates)
- Fleet inventory and GPS tracking
- Client registry with service history
- Media uploads to Cloudflare R2
- Dashboard stats aggregation
- Analytics endpoints
- WebSocket location stream

### Baseline Implementations 🔄
- Analytics (can be evolved into event-driven read models)
- Notifications (static data, can be connected to event stream)

### Pending Features
- Driver management endpoints (service exists, routes need implementation)
- Settings/billing configuration endpoints
- CSV export for trip history
- Advanced filtering and search
- Pagination for large datasets

---

## 📚 Additional Resources

- **Frontend Documentation:** See `FrontendGruaService/README.md`
- **API Endpoint Details:** See `FrontendGruaService/README_API_ENDPOINTS.md`
- **Postman Collection:** Import `grua-media.postman_collection.json` for API testing
- **FastAPI Docs:** https://fastapi.tiangolo.com/

---

*Built with FastAPI, PostgreSQL, and Docker Compose for scalable towing dispatch management.*
