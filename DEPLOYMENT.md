# Deployment Guide

## Vercel Deployment (Frontend)

### Option 1: Using Vercel Dashboard (Recommended)

1. **Import Your Repository**
   - Go to https://vercel.com/new
   - Import your GitHub repository

2. **Configure Project Settings**
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend` (IMPORTANT!)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)

3. **Environment Variables**
   Add these environment variables in the Vercel dashboard:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-api.com
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
   NEXT_PUBLIC_APP_URL=https://your-domain.vercel.app
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait for the build to complete
   - Your app will be live at `https://your-project.vercel.app`

### Option 2: Using Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to frontend directory
cd frontend

# Deploy
vercel

# Follow the prompts:
# - Set up and deploy? Y
# - Which scope? Select your account
# - Link to existing project? N (first time) or Y
# - What's your project's name? trendchecker
# - In which directory is your code located? ./
# - Want to override settings? N

# For production deployment:
vercel --prod
```

### Troubleshooting

**404 NOT_FOUND Error:**
- Make sure "Root Directory" is set to `frontend` in Vercel project settings
- Go to: Project Settings → General → Root Directory → `frontend`
- Redeploy after changing this setting

**Build Failures:**
- Check that all environment variables are set
- Ensure `npm install` works locally in the frontend directory
- Check build logs in Vercel dashboard for specific errors

**CSS/Styling Issues:**
- Clear Vercel cache and redeploy
- Ensure Tailwind CSS is properly configured
- Check that all dependencies are in `package.json`

---

## Railway/Render Deployment (Backend)

### Railway

1. **Create New Project**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Configure Service**
   - **Root Directory**: `backend`
   - **Build Command**: Leave empty (uses Dockerfile or Procfile)
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Environment Variables**
   ```
   DATABASE_URL=postgresql://...
   REDIS_URL=redis://...
   JWT_SECRET_KEY=your-secret-key
   STRIPE_API_KEY=sk_live_...
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USERNAME=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   SMTP_FROM_EMAIL=noreply@yourdomain.com
   ```

4. **Add Database**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway will automatically add DATABASE_URL

5. **Add Redis**
   - Click "New" → "Database" → "Redis"
   - Railway will automatically add REDIS_URL

6. **Deploy**
   - Railway will auto-deploy on every push to main branch

### Render

1. **Create Web Service**
   - Go to https://render.com
   - Click "New" → "Web Service"
   - Connect your GitHub repository

2. **Configure**
   - **Name**: trendchecker-api
   - **Root Directory**: `backend`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

3. **Add PostgreSQL**
   - Create new PostgreSQL database
   - Copy connection string to DATABASE_URL

4. **Add Redis**
   - Create new Redis instance
   - Copy connection string to REDIS_URL

5. **Environment Variables**
   Same as Railway above

---

## Environment Variables Reference

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000              # Local development
NEXT_PUBLIC_API_URL=https://api.yourdomain.com         # Production
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...         # Test key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...         # Live key
NEXT_PUBLIC_APP_URL=http://localhost:3000              # Local
NEXT_PUBLIC_APP_URL=https://yourdomain.com             # Production
```

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_REFRESH_SECRET_KEY=another-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Stripe
STRIPE_API_KEY=sk_test_...                            # Test key
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxx
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME=TrendChecker

# App
APP_NAME=TrendChecker
APP_VERSION=1.0.0
DEBUG=False
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

---

## Quick Fix for Your Current Error

Since you're getting a 404 error on Vercel, do this immediately:

1. Go to your Vercel project dashboard
2. Click on "Settings" tab
3. Scroll to "Root Directory"
4. Click "Edit"
5. Enter: `frontend`
6. Click "Save"
7. Go to "Deployments" tab
8. Click the three dots on the latest deployment
9. Click "Redeploy"

This should fix the 404 error!

---

## Testing Deployments

### Frontend
```bash
# Check if the site loads
curl -I https://your-domain.vercel.app

# Should return 200 OK
```

### Backend
```bash
# Health check
curl https://your-api-domain.com/health

# Should return: {"status":"healthy","version":"1.0.0"}
```

---

## DNS Configuration

Once deployed, configure your custom domain:

### For Vercel (Frontend)
1. Go to Project Settings → Domains
2. Add your domain (e.g., `app.yourdomain.com`)
3. Follow DNS instructions to add:
   - CNAME record: `app` → `cname.vercel-dns.com`

### For Backend API
1. In Railway/Render, go to Settings → Networking
2. Add custom domain (e.g., `api.yourdomain.com`)
3. Add DNS records:
   - CNAME record: `api` → provided by hosting platform

---

## Monitoring

- **Frontend**: Check Vercel Analytics dashboard
- **Backend**: Add monitoring with services like:
  - Sentry (error tracking)
  - LogRocket (session replay)
  - DataDog (APM)

---

## Continuous Deployment

Both Vercel and Railway support automatic deployments:

- **Main Branch**: Auto-deploys to production
- **Other Branches**: Creates preview deployments
- **Pull Requests**: Automatic preview URLs

Configure branch settings in your hosting dashboard.
