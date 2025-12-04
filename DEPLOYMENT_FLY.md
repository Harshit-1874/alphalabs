# Fly.io Deployment Guide for AlphaLabs

## Prerequisites

1. Install Fly.io CLI:
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   
   # Or download from: https://fly.io/docs/getting-started/installing-flyctl/
   ```

2. Sign up for Fly.io account: https://fly.io/app/sign-up

## Backend Deployment Commands

### 1. Login to Fly.io
```bash
fly auth login
```

### 2. Navigate to Backend Directory
```bash
cd backend
```

### 3. Initialize Fly.io App (First Time Only)
```bash
fly launch
```
This will:
- Ask for app name (or use default)
- Ask for region (choose closest to you)
- Detect Python and create fly.toml
- Ask if you want to deploy now (say no for now)

### 4. Set Environment Variables
```bash
# Set all your environment variables
fly secrets set OPENROUTER_API_KEY=your_key_here
fly secrets set SUPABASE_URL=https://your-project.supabase.co
fly secrets set SUPABASE_KEY=your_supabase_key
fly secrets set DATABASE_URL=postgresql://user:pass@host:5432/dbname
fly secrets set CLERK_SECRET_KEY=sk_test_your_key
fly secrets set CLERK_WEBHOOK_SECRET=whsec_your_secret
fly secrets set ENCRYPTION_KEY=your_fernet_key
fly secrets set CERTIFICATE_SHARE_BASE_URL=https://your-frontend-domain.vercel.app/verify
fly secrets set WEBSOCKET_BASE_URL=wss://your-backend-app.fly.dev
```

Or set multiple at once:
```bash
fly secrets set \
  OPENROUTER_API_KEY=your_key \
  SUPABASE_URL=https://your-project.supabase.co \
  SUPABASE_KEY=your_key \
  DATABASE_URL=postgresql://... \
  CLERK_SECRET_KEY=sk_test_... \
  CLERK_WEBHOOK_SECRET=whsec_... \
  ENCRYPTION_KEY=your_key \
  CERTIFICATE_SHARE_BASE_URL=https://your-frontend.vercel.app/verify \
  WEBSOCKET_BASE_URL=wss://your-backend-app.fly.dev
```

### 5. Deploy Backend
```bash
fly deploy
```

### 6. Check Deployment Status
```bash
fly status
fly logs
```

### 7. Get Your Backend URL
```bash
fly info
# Your app will be available at: https://your-app-name.fly.dev
```

## Frontend Deployment (Vercel)

### 1. Install Vercel CLI (Optional)
```bash
npm i -g vercel
```

### 2. Navigate to Frontend Directory
```bash
cd frontend
```

### 3. Deploy to Vercel
```bash
vercel
```

Or connect via GitHub:
1. Go to https://vercel.com
2. Import your repository
3. Set root directory to `frontend`
4. Add environment variables:
   - `NEXT_PUBLIC_API_URL=https://your-backend-app.fly.dev`
   - `NEXT_PUBLIC_WS_URL=wss://your-backend-app.fly.dev`

### 4. Update Frontend Environment Variables
In Vercel dashboard → Your Project → Settings → Environment Variables:
```
NEXT_PUBLIC_API_URL=https://your-backend-app.fly.dev
NEXT_PUBLIC_WS_URL=wss://your-backend-app.fly.dev
```

## Important Notes

### WebSocket URLs
- **Development**: `ws://localhost:5000`
- **Production**: `wss://your-backend-app.fly.dev` (note the `wss://` for secure WebSocket)

### CORS Configuration
The CORS configuration is now managed via the `CORS_ALLOWED_ORIGINS` environment variable. By default, it includes `http://localhost:3000` and `https://alphalabs-frontend-oky2.vercel.app`.

To customize allowed origins (e.g., for preview deployments), set the environment variable:
```bash
fly secrets set CORS_ALLOWED_ORIGINS="http://localhost:3000,https://your-frontend.vercel.app,https://your-preview.vercel.app"
```

Or set it in your `.env` file for local development:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
```

### Fly.io Free Tier Limits
- 3 shared VMs (256MB RAM each)
- 160GB outbound data transfer
- Your backend will use 1 VM (512MB RAM as configured)

### Useful Fly.io Commands
```bash
# View logs
fly logs

# SSH into your app
fly ssh console

# Scale your app
fly scale count 1
fly scale memory 512

# Check app status
fly status

# Open app in browser
fly open

# View secrets (names only, not values)
fly secrets list
```

## Troubleshooting

### WebSocket Connection Issues
1. Make sure you're using `wss://` (secure WebSocket) in production
2. Check Fly.io logs: `fly logs`
3. Verify CORS settings include your frontend domain

### Database Connection Issues
1. Ensure your Supabase database allows connections from Fly.io IPs
2. Check DATABASE_URL format: `postgresql://user:pass@host:5432/dbname`
3. Verify database credentials in Fly.io secrets

### Port Issues
- Fly.io automatically sets PORT environment variable
- Your app should read from `os.getenv('PORT', 8080)`
- The fly.toml sets internal_port to 8080

