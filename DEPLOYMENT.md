# Deployment Guide

## Overview

This guide covers deploying the Telegram Beauty Salon Bot in production with:

- Webhook mode for Telegram bot
- Stripe webhook endpoint
- Redis-backed APScheduler for horizontal scaling
- Docker Compose for local deployment
- Vercel/Render deployment options

## Prerequisites

- Docker and Docker Compose installed
- Supabase project with database tables created
- Stripe account with webhook endpoint configured
- Redis instance (or use Docker Compose Redis)

## Environment Variables

Create a `.env` file with the following variables:

```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token
BOT_WEBHOOK_URL=https://your-domain.com/webhook/telegram

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Claude AI
CLAUDE_API_KEY=sk-ant-...

# Redis (for APScheduler cluster)
REDIS_URL=redis://redis:6379/0

# Admin (comma-separated Telegram user IDs)
ADMIN_TELEGRAM_IDS=123456789,987654321

# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=production
```

## Local Deployment with Docker Compose

### 1. Start Services

```bash
docker-compose up -d
```

This starts:

- `bot`: Telegram bot service
- `webhook`: Stripe webhook handler
- `redis`: Redis for APScheduler cluster

### 2. Check Logs

```bash
# Bot logs
docker-compose logs -f bot

# Webhook logs
docker-compose logs -f webhook

# Redis logs
docker-compose logs -f redis
```

### 3. Stop Services

```bash
docker-compose down
```

## Production Deployment

### Option 1: Vercel/Render (Serverless)

#### Setup Webhook Endpoint

1. Deploy `webhook.py` as a serverless function
2. Configure Stripe webhook to point to: `https://your-domain.com/webhook/stripe`
3. Set `BOT_WEBHOOK_URL` in environment variables

#### Vercel Configuration

Create `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "webhook.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/webhook/stripe",
      "dest": "webhook.py"
    },
    {
      "src": "/health",
      "dest": "webhook.py"
    }
  ]
}
```

#### Render Configuration

Create `render.yaml`:

```yaml
services:
  - type: web
    name: telegram-bot-webhook
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python webhook.py
    envVars:
      - key: BOT_TOKEN
        sync: false
      - key: STRIPE_WEBHOOK_SECRET
        sync: false
      # ... other env vars
```

### Option 2: Traditional VPS/Server

1. Clone repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` file
4. Run with systemd or supervisor:

```ini
[Unit]
Description=Telegram Beauty Salon Bot
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/telegram-bot
EnvironmentFile=/opt/telegram-bot/.env
ExecStart=/opt/telegram-bot/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Testing Webhook Locally (ngrok)

For local testing of webhooks:

1. Install ngrok: `brew install ngrok` or download from ngrok.com
2. Start bot locally: `python bot.py`
3. Start ngrok tunnel:

```bash
ngrok http 8000
```

1. Use ngrok URL in Stripe webhook configuration:
   - Stripe webhook: `https://your-ngrok-url.ngrok.io/webhook/stripe`
   - Bot webhook: `https://your-ngrok-url.ngrok.io/webhook/telegram`

2. Update `.env`:

```env
BOT_WEBHOOK_URL=https://your-ngrok-url.ngrok.io/webhook/telegram
```

## Horizontal Scaling

The bot supports horizontal scaling with Redis:

1. Multiple bot instances can run simultaneously
2. APScheduler uses Redis as job store
3. Only one instance processes reminders (coordinated via Redis)

### Scaling Setup

```bash
# Start multiple bot instances
docker-compose up -d --scale bot=3
```

Each instance:

- Shares the same Redis backend
- Processes Telegram updates independently
- Coordinates scheduled jobs via Redis

## Security Checklist

- [ ] Stripe webhook signature verification enabled
- [ ] Rate limiting configured
- [ ] HTTPS enforced in production
- [ ] Admin Telegram IDs configured
- [ ] Supabase RLS policies configured
- [ ] Environment variables secured (not in git)
- [ ] Webhook endpoints protected

## Monitoring

### Health Checks

- Bot health: `GET /health` (if webhook mode)
- Webhook health: `GET /health` on webhook service

### Logs

Monitor logs for:

- Webhook signature verification failures
- Rate limit violations
- Database connection errors
- Payment processing errors

## Troubleshooting

### Webhook Not Receiving Updates

1. Check `BOT_WEBHOOK_URL` is set correctly
2. Verify webhook endpoint is accessible
3. Check Telegram Bot API webhook status: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Stripe Webhook Failures

1. Verify `STRIPE_WEBHOOK_SECRET` matches Stripe dashboard
2. Check webhook endpoint is accessible
3. Review webhook logs for signature errors

### Redis Connection Issues

1. Verify `REDIS_URL` is correct
2. Check Redis is running: `docker-compose ps redis`
3. Test connection: `redis-cli -u $REDIS_URL ping`

## Supabase RLS Setup

Configure Row Level Security policies in Supabase SQL Editor:

```sql
-- Enable RLS
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE slots ENABLE ROW LEVEL SECURITY;

-- Clients: users can only see their own data
CREATE POLICY "Users can view own client data"
ON clients FOR SELECT
USING (auth.uid()::text = telegram_id::text);

-- Bookings: users can only see their own bookings
CREATE POLICY "Users can view own bookings"
ON bookings FOR SELECT
USING (client_id IN (
    SELECT id FROM clients
    WHERE telegram_id::text = auth.uid()::text
));

-- Slots: all authenticated users can view available slots
CREATE POLICY "Users can view available slots"
ON slots FOR SELECT
USING (true);
```

Note: Service role key bypasses RLS for admin operations.
