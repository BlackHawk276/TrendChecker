# TrendChecker - E-Commerce Intelligence SaaS Platform

> Discover trending e-commerce stores with AI-powered insights

A professional monorepo built with Turborepo, featuring a Next.js 14 frontend and FastAPI backend.

## 🏗️ Project Structure

```
TrendChecker/
├── apps/
│   ├── web/              # Next.js 14 Frontend
│   │   ├── src/
│   │   │   ├── app/      # Next.js App Router
│   │   │   ├── components/
│   │   │   ├── lib/      # API client, utils
│   │   │   └── types/    # TypeScript types
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── api/              # FastAPI Backend
│       ├── app/
│       │   ├── models/   # SQLAlchemy models
│       │   ├── routers/  # API routes
│       │   ├── services/ # Business logic
│       │   └── schemas/  # Pydantic schemas
│       ├── alembic/      # Database migrations
│       ├── scripts/      # Utility scripts
│       └── requirements.txt
│
├── packages/
│   └── shared/           # Shared TypeScript types & utils
│       ├── src/
│       │   ├── types.ts  # Shared type definitions
│       │   └── index.ts  # Exports
│       └── package.json
│
├── package.json          # Root workspace config
├── turbo.json           # Turborepo pipeline config
└── DEPLOYMENT.md        # Deployment guide
```

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm 9+
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Clone the repository
git clone https://github.com/BlackHawk276/TrendChecker.git
cd TrendChecker

# Install all dependencies (both apps)
npm install

# Install backend Python dependencies
cd apps/api
pip install -r requirements.txt
cd ../..
```

### Development

```bash
# Run both frontend and backend in parallel
npm run dev

# Or run individually:
npm run web:dev   # Frontend only (localhost:3000)
npm run api:dev   # Backend only (localhost:8000)
```

### Building

```bash
# Build all apps
npm run build

# Build specific app
npm run build --workspace=apps/web
```

## 📦 Apps & Packages

### `apps/web` - Frontend

**Tech Stack:**
- Next.js 14 (App Router)
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui
- React Query
- Zustand

**Features:**
- 🎨 Beautiful landing page with gradients
- 🌓 Dark mode support
- 📱 Fully responsive design
- 🔐 JWT authentication
- 📊 Real-time analytics dashboard
- ⭐ Save and track stores
- 🔔 Smart alerts system

**Development:**
```bash
cd apps/web
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # Run ESLint
```

### `apps/api` - Backend

**Tech Stack:**
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Redis
- Alembic (migrations)
- JWT authentication
- Celery (background tasks)

**Features:**
- 🔥 Intelligent trending score algorithm
- 🏪 Store discovery and analysis
- 🔐 Complete auth system (JWT + API keys)
- 📧 Email notifications
- 💾 Redis caching
- 📊 Usage tracking
- 🔔 Alert system

**Development:**
```bash
cd apps/api
uvicorn app.main:app --reload   # Start dev server
alembic upgrade head             # Run migrations
python scripts/calculate_trending.py  # Calculate trending scores
```

### `packages/shared` - Shared Code

Shared TypeScript types and utilities used by both frontend and backend.

**Exports:**
- Type definitions (Store, User, Product, etc.)
- Utility functions (formatNumber, formatCurrency, slugify)

**Usage:**
```typescript
import { Store, formatNumber } from '@trendchecker/shared';
```

## 🔧 Configuration

### Environment Variables

#### Frontend (`apps/web/.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

#### Backend (`apps/api/.env`)
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trendchecker
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key
STRIPE_API_KEY=sk_test_...
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

See `DEPLOYMENT.md` for complete environment variable reference.

## 📝 Available Scripts

### Root Level

```bash
npm run dev          # Run all apps in dev mode
npm run build        # Build all apps
npm run lint         # Lint all apps
npm run test         # Test all apps
npm run clean        # Clean all build artifacts
npm run format       # Format code with Prettier
npm run web:dev      # Frontend only
npm run api:dev      # Backend only (requires separate terminal)
```

### Turborepo Commands

```bash
turbo run build                    # Build all apps
turbo run build --filter=web       # Build only web app
turbo run dev --parallel           # Run all dev servers in parallel
turbo run lint --continue          # Lint all, don't stop on errors
```

## 🚢 Deployment

### Frontend (Vercel)

1. Import repository in Vercel
2. **Set Root Directory to:** `apps/web` ⚠️ **IMPORTANT!**
3. Framework Preset: Next.js (auto-detected)
4. Add environment variables
5. Deploy!

**Vercel Configuration:**
- Root Directory: `apps/web`
- Build Command: `npm run build` (default)
- Output Directory: `.next` (default)
- Install Command: `npm install` (default)

### Backend (Railway/Render)

1. Create new service
2. **Set Root Directory to:** `apps/api`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add PostgreSQL and Redis databases
6. Set environment variables
7. Deploy!

**See `DEPLOYMENT.md` for detailed deployment instructions.**

## 🧪 Testing

```bash
# Frontend tests
cd apps/web
npm test

# Backend tests
cd apps/api
pytest
```

## 📚 Documentation

- [Deployment Guide](./DEPLOYMENT.md) - Complete deployment instructions
- [Backend README](./apps/api/README.md) - Backend API documentation
- [Frontend README](./apps/web/README.md) - Frontend documentation
- [Trending Algorithm](./apps/api/docs/TRENDING_ALGORITHM.md) - Scoring algorithm details

## 🏗️ Tech Stack

### Frontend
- ⚛️ React 19
- ⚡ Next.js 14 (App Router)
- 🎨 Tailwind CSS
- 🧩 shadcn/ui
- 📡 React Query
- 🐻 Zustand
- 📊 Recharts
- 🎭 Framer Motion

### Backend
- 🐍 Python 3.11
- ⚡ FastAPI
- 🗄️ PostgreSQL
- 🔄 SQLAlchemy (async)
- 🔴 Redis
- 📧 SendGrid
- 💳 Stripe

### DevOps
- 🏗️ Turborepo
- 📦 npm workspaces
- 🔄 Alembic migrations
- 🐳 Docker (optional)

## 🤝 Contributing

1. Clone the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- 📧 Email: support@trendchecker.com
- 🐛 GitHub Issues: [Report a bug](https://github.com/BlackHawk276/TrendChecker/issues)
- 📖 Documentation: [Full docs](https://docs.trendchecker.com)

---

Built with ❤️ using Turborepo, Next.js, and FastAPI
