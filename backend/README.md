# E-Commerce Intelligence SaaS - Backend API

Production-ready FastAPI backend for tracking and analyzing e-commerce stores and products.

## Features

- **Async FastAPI** with modern Python 3.11+ features
- **PostgreSQL** with async SQLAlchemy ORM
- **Alembic** database migrations
- **UUID** primary keys for better security
- **JSONB** fields for flexible data storage
- **Comprehensive models** for stores, products, users, and alerts
- **Subscription management** with Stripe integration
- **API key authentication** support
- **CORS** configured for frontend integration
- **Type hints** throughout the codebase

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Settings and configuration
│   ├── database.py          # Database connection and session management
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── store.py         # Store model
│   │   ├── product.py       # Product model
│   │   ├── user.py          # User model with subscriptions
│   │   ├── saved_store.py   # User saved stores association
│   │   └── alert.py         # User alerts/notifications
│   ├── routers/             # API route handlers (to be added)
│   ├── services/            # Business logic (to be added)
│   ├── scrapers/            # Web scraping utilities (to be added)
│   └── utils/               # Helper functions (to be added)
├── alembic/                 # Database migrations
│   ├── versions/            # Migration scripts
│   └── env.py              # Alembic environment config
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── alembic.ini             # Alembic configuration
└── README.md               # This file
```

## Database Models

### Store Model
Tracks e-commerce stores with metrics and metadata:
- Basic info: domain, name, description, category
- Metrics: product_count, trending_score, growth_rate, revenue estimates
- Technology: theme_name, tech_stack, social_links
- Flexible JSONB metadata field

### Product Model
Individual products from stores:
- Product details: title, description, vendor, product_type
- Pricing: price, compare_at_price, currency
- Images and tags
- Availability tracking
- First/last seen timestamps

### User Model
User accounts with subscription management:
- Authentication: email, hashed_password, api_key
- Profile: full_name, avatar_url
- Subscription: tier (free/starter/pro/agency), status, Stripe integration
- Usage tracking: searches_used_this_month, searches_limit

### SavedStore Model
User-store bookmarking with notes

### Alert Model
User-configured notifications for:
- New stores in categories
- Price drops
- New products added

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Key settings to configure:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Application secret key
- `JWT_SECRET_KEY`: JWT token secret
- `STRIPE_API_KEY`: Stripe API key
- `REDIS_URL`: Redis connection string

### 3. Set Up Database

Create a PostgreSQL database:

```bash
createdb ecommerce_saas
```

Run migrations:

```bash
alembic upgrade head
```

### 4. Run the Application

Development mode:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
python -m app.main
```

Production mode:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback migration:

```bash
alembic downgrade -1
```

View migration history:

```bash
alembic history
```

## Subscription Tiers

The platform supports 4 subscription tiers:

| Tier     | Monthly Searches | Features |
|----------|------------------|----------|
| Free     | 10               | Basic search |
| Starter  | 100              | Enhanced analytics |
| Pro      | 1,000            | API access, alerts |
| Agency   | 10,000           | White-label, priority support |

## Development Roadmap

### Phase 1: Core API (Current)
- ✅ Database models and migrations
- ✅ Application configuration
- ⏳ Authentication endpoints
- ⏳ Store and product CRUD operations

### Phase 2: Scraping & Data Collection
- ⏳ Shopify store detection
- ⏳ Product scraping utilities
- ⏳ Celery tasks for background jobs
- ⏳ Redis caching layer

### Phase 3: Intelligence Features
- ⏳ Trending score calculation
- ⏳ Growth rate analysis
- ⏳ Category insights
- ⏳ Alert system implementation

### Phase 4: Subscription & Payments
- ⏳ Stripe webhook handlers
- ⏳ Usage tracking middleware
- ⏳ Subscription upgrade/downgrade flows

## Technology Stack

- **FastAPI** 0.104.1 - Modern web framework
- **SQLAlchemy** 2.0.23 - Async ORM
- **Alembic** 1.12.1 - Database migrations
- **PostgreSQL** - Primary database (via asyncpg)
- **Pydantic** 2.5.0 - Data validation
- **Python-Jose** - JWT authentication
- **Passlib** - Password hashing
- **Stripe** - Payment processing
- **Redis** - Caching and Celery broker
- **Celery** - Background task processing
- **BeautifulSoup4** - Web scraping
- **HTTPX** - Async HTTP client

## Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Submit a pull request

## License

Proprietary - All rights reserved
