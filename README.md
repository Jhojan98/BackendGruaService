# Terra Towing Backend (FastAPI Microservices)

This backend is a FastAPI microservices foundation for FrontendGruaService.

## Architecture

- `gateway` (port 8000): Public API entrypoint (`/api/v1/*`), JWT verification, route aggregation.
- `services/auth-service` (port 8001): Login, token verification, user profile.
- `services/dispatch-service` (port 8002): Trips lifecycle (list, create, status, assign).
- `services/fleet-service` (port 8003): Fleet inventory, status, locations, WebSocket location stream.
- `services/clients-service` (port 8004): Clients registry and client service history.
- `services/media-service` (port 8005): Image uploads to Cloudflare R2 and metadata registry.
- `postgres` (port 5432): Single PostgreSQL server with separate databases per service.

## Database Isolation

Databases are created by `infra/postgres/init/01-create-databases.sql`:

- `auth_db`
- `dispatch_db`
- `fleet_db`
- `clients_db`
- `media_db`

Each service only reads/writes its own database.

## Where Database Fields Are Defined

Database creation happens in two levels:

1. Database containers and isolated databases:
	 - `docker-compose.yml` starts PostgreSQL.
	 - `infra/postgres/init/01-create-databases.sql` creates `auth_db`, `dispatch_db`, `fleet_db`, `clients_db`.
2. Table and field creation:
	 - Each service runs `Base.metadata.create_all(bind=engine)` on startup.
	 - Table schemas are defined in each service `app/models.py`.

Current table field definitions:

- Auth DB (`services/auth-service/app/models.py`)
	- `users`: `id`, `email`, `full_name`, `role`, `password_hash`, `profile_image_url`, `theme`, `language`, `email_alerts`, `sms_urgent_alerts`, `browser_notifications`, `employee_id`, `office_location`
- Dispatch DB (`services/dispatch-service/app/models.py`)
	- `trips`: `id`, `client_id`, `client_name`, `origin`, `destination`, `distance`, `status`, `tow_truck`, `date`, `time`
- Fleet DB (`services/fleet-service/app/models.py`)
	- `trucks`: `id`, `unit_number`, `truck_type`, `status`, `lat`, `lng`
- Clients DB (`services/clients-service/app/models.py`)
	- `clients`: `id`, `name`, `membership`, `phone`
	- `client_history`: `id`, `client_id`, `service_date`, `description`, `revenue`
- Media DB (`services/media-service/app/models.py`)
	- `media_assets`: `id`, `entity_type`, `entity_id`, `original_filename`, `mime_type`, `file_size_bytes`, `r2_key`, `url`, `access_mode`, `uploaded_by`, `created_at`, `updated_at`

## Single File for Initial Data

You can now edit all initial records in one file:

- `seed-data/initial_data.json`

This file contains seed data for all databases:

- `auth.users`
- `dispatch.trips`
- `fleet.trucks`
- `clients.clients`
- `clients.history`

How it is used:

- On startup, each service reads `seed-data/initial_data.json`.
- If its table is empty, it inserts data from this file.
- If the file is missing/invalid JSON, no seed data is inserted.

To apply changes in seed file to a fresh database:

```bash
docker compose down -v
docker compose up --build
```

## Service Structure (Separated Logic)

Each microservice now follows this structure:

- `app/config.py`: environment configuration
- `app/database.py`: SQLAlchemy engine/session/base
- `app/models.py`: table classes (database schema)
- `app/schemas.py`: request/response DTOs
- `app/service.py`: business logic and seed logic
- `app/main.py`: API routes only (thin controller)

## API Coverage

Implemented in gateway (`/api/v1`):

- `POST /auth/login`
- `GET /users` (admin role required)
- `GET /users/me`
- `PATCH /users/me` (JSON or multipart form-data with optional `file` for profile image upload via media-service)
- `PATCH /users/{id}` (admin role required; JSON or multipart form-data with optional `file`)
- `POST /users` (admin role required)
- `GET /notifications`
- `GET /dashboard/stats`
- `GET /dashboard/quick-actions`
- `GET /trips`
- `GET /trips/{id}`
- `POST /trips`
- `PUT /trips/{id}/status`
- `PUT /trips/{id}/assign`
- `GET /fleet`
- `GET /fleet/{id}`
- `GET /fleet/locations`
- `GET /clients`
- `POST /clients` (admin role required)
- `GET /clients/{id}/history`
- `POST /media/upload` (multipart image upload)
- `GET /media/{id}`
- `GET /media/by-entity?entity_type=...&entity_id=...`
- `GET /analytics/revenue`
- `GET /analytics/performance`

Service-level health checks:

- `GET /api/health` on gateway
- `GET /health` on each microservice

Fleet WebSocket stream (direct service endpoint):

- `ws://localhost:8003/ws/locations`

## Quick Start

1. Ensure Docker Desktop is running.
2. From this folder, run:

```bash
docker compose up --build
```

3. Open docs:

- Gateway docs: `http://localhost:8000/docs`
- Auth service docs: `http://localhost:8001/docs`
- Dispatch service docs: `http://localhost:8002/docs`
- Fleet service docs: `http://localhost:8003/docs`
- Clients service docs: `http://localhost:8004/docs`
- Media service docs: `http://localhost:8005/docs`

## Testing

Integration tests are available under `tests/` and target the running gateway (`http://localhost:8000` by default).

Install test dependencies:

```bash
pip install -r tests/requirements-test.txt
```

Run all tests:

```bash
pytest
```

Optional custom gateway URL:

```bash
API_BASE_URL=http://localhost:8000 pytest
```

## Seed Users

- Admin:
	- email: `admin@terra.local`
	- password: `admin123`
- Dispatcher:
	- email: `dispatcher@terra.local`
	- password: `dispatch123`

Use `POST /api/v1/auth/login` to get a bearer token.

## User Profile and User Creation

- `PATCH /api/v1/users/me` supports two body formats:
	- `application/json` for profile/preferences updates.
	- `multipart/form-data` for profile/preferences and optional profile image upload in `file`.
- When `file` is sent, gateway uploads the image internally to media-service and persists the returned URL in `profile_image_url`.
- `POST /api/v1/users` creates new users and requires admin role.
- `GET /api/v1/users` lists all users and requires admin role.
- `PATCH /api/v1/users/{id}` updates any user and requires admin role.

## Notes

- CORS is enabled for development.
- Analytics and notifications are currently baseline implementations and can be evolved into event-driven read models.
- Fleet real-time updates are available via WebSocket in fleet service.
