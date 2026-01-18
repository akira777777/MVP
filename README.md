# Telegram Beauty Salon Booking Bot MVP

Production-ready Telegram bot for beauty salon appointment booking with payments, reminders, and AI Q&A.

## 🏗️ Architecture

```
telegram-beauty-salon-bot/
├── bot/                    # Bot handlers and FSM states
│   ├── handlers.py         # Main message/callback handlers
│   ├── keyboards.py        # Inline keyboard builders
│   └── states.py           # FSM state definitions
├── db/                     # Database layer
│   └── supabase_client.py  # Supabase CRUD operations
├── models/                 # Pydantic models
│   ├── booking.py          # Booking models
│   ├── client.py           # Client models
│   ├── slot.py             # Time slot models
│   └── service.py          # Service definitions
├── payments/               # Payment processing
│   └── stripe.py           # Stripe integration
├── scheduler/              # Task scheduling
│   └── reminders.py        # Appointment reminders
├── utils/                  # Utilities
│   └── ai_qa.py            # Claude AI integration
├── tests/                  # E2E tests
│   └── test_e2e.py         # Playwright tests
├── bot.py                  # Main entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container definition
└── docker-compose.yml      # Docker Compose setup
```

## 🤖 Parallel Agents & Automation

### Composer Integration

Use Cursor Composer (Ctrl+K) with parallel agents:

**Quick Prompts (Vibe Mode):**
```
@agent1 Architect plan
@agent2 Code handlers
@tester Run Playwright
```

**Parallel Spawn:**
```
Spawn 5 agents: 2 coders (bot/db), 1 tester, 1 devops (docker), 1 reviewer.
```

**Iterative Fixes:**
```
Fix bug: overbooking → Apply → @web search GDPR Telegram
```

See [COMPOSER_PROMPTS.md](COMPOSER_PROMPTS.md) for detailed prompts.

### TMUX Agents (20 Terminals)

```bash
# Setup 20 parallel agent terminals
python tmux_agents_parallel.py setup

# List active agents
python tmux_agents_parallel.py list

# Attach to session
tmux attach -t agents
```

Each terminal runs a Cursor chat agent with specific task.

### Auto Test & Deploy

```bash
# Run full pipeline: test → build → deploy
python scripts/auto_test_deploy.py

# Or use GitHub Actions (automatic on push)
# See .github/workflows/auto_deploy.yml
```

**Pipeline Steps:**
1. ✅ Linter (ruff)
2. ✅ Tests (pytest + Playwright)
3. ✅ Docker build
4. ✅ Deploy (Docker/Vercel)
5. ✅ Create PR (via MCP GitHub)
6. ✅ Deploy to Vercel (via MCP)

### MCP GitHub Integration

Configure MCP GitHub server in `.kilocode/mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

**Usage:**
- Create PR: `MCP GitHub: Create pull request`
- Deploy: `MCP GitHub: Trigger Vercel deployment`

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- Supabase account (free tier)
- Stripe account (test mode)
- Claude API key

### Installation

1. **Clone and setup:**

```bash
git clone <repository-url>
cd telegram-beauty-salon-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
```env
BOT_TOKEN=your_telegram_bot_token
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
CLAUDE_API_KEY=sk-ant-...
```

3. **Setup Supabase database:**

Run these SQL commands in Supabase SQL Editor:

```sql
-- Clients table
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT,
    phone TEXT,
    email TEXT,
    gdpr_consent BOOLEAN DEFAULT FALSE,
    gdpr_consent_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Slots table
CREATE TABLE slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'available' CHECK (status IN ('available', 'booked', 'cancelled', 'completed')),
    service_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Bookings table
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    slot_id UUID REFERENCES slots(id) ON DELETE CASCADE,
    service_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'paid', 'cancelled', 'completed', 'no_show')),
    price_czk INTEGER NOT NULL,
    stripe_payment_intent_id TEXT,
    stripe_payment_status TEXT,
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_sent_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_clients_telegram_id ON clients(telegram_id);
CREATE INDEX idx_slots_service_status ON slots(service_type, status);
CREATE INDEX idx_slots_start_time ON slots(start_time);
CREATE INDEX idx_bookings_client_id ON bookings(client_id);
CREATE INDEX idx_bookings_slot_id ON bookings(slot_id);
CREATE INDEX idx_bookings_status ON bookings(status);
```

4. **Run the bot:**

```bash
python bot.py
```

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop
docker-compose down
```

## 📋 Features

### ✅ Core Features

- **Service Booking**: Select from 4 services (Manicure, Haircut, Pedicure, Facial)
- **Calendar Slots**: View and book available time slots
- **Stripe Payments**: Secure payment processing
- **Appointment Reminders**: Automatic 24h reminders via Telegram
- **AI Q&A**: Claude-powered customer support
- **GDPR Compliance**: Consent screen and data protection

### 🔄 Booking Flow

1. User sends `/start`
2. GDPR consent screen (first time)
3. Main menu with options
4. Select service → Select slot → Confirm → Pay
5. Receive confirmation and reminder

### 💳 Payment Flow

1. Booking created with status `pending`
2. Stripe PaymentIntent created
3. User redirected to Stripe Checkout
4. Webhook updates booking to `paid` on success
5. Slot marked as `booked`

### 🔔 Reminder System

- APScheduler runs hourly
- Checks bookings 24h before appointment
- Sends Telegram reminder
- Marks reminder as sent

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio playwright

# Install Playwright browsers
playwright install

# Run tests
pytest tests/ -v
```

## 📊 Database Schema (ERD)

See [ERD.md](ERD.md) for detailed entity relationship diagram.

**Entities:**
- `clients` - User/client information
- `slots` - Available time slots
- `bookings` - Appointment bookings

**Relationships:**
- `clients` 1:N `bookings`
- `slots` 1:N `bookings`

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token | ✅ |
| `SUPABASE_URL` | Supabase project URL | ✅ |
| `SUPABASE_KEY` | Supabase anon key | ✅ |
| `STRIPE_SECRET_KEY` | Stripe secret key | ✅ |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | ✅ |
| `CLAUDE_API_KEY` | Claude API key | ✅ |
| `TIMEZONE` | Timezone (default: Europe/Prague) | ❌ |
| `REMINDER_HOURS_BEFORE` | Hours before reminder (default: 24) | ❌ |

### Services & Pricing

- **Manicure**: 150 CZK, 60 minutes
- **Haircut & Styling**: 200 CZK, 90 minutes
- **Pedicure**: 180 CZK, 75 minutes
- **Facial Treatment**: 250 CZK, 60 minutes

## 🚢 Deployment

### GitHub Actions CI/CD

The project includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that:

1. Runs tests and linter
2. Builds Docker image
3. Deploys to your server (configure SSH/Vercel)

### Manual Deployment

1. **Build Docker image:**
```bash
docker build -t telegram-beauty-salon-bot .
```

2. **Run container:**
```bash
docker run -d \
  --name beauty-salon-bot \
  --env-file .env \
  telegram-beauty-salon-bot
```

3. **Setup Stripe Webhook:**
   - URL: `https://your-domain.com/webhook/stripe`
   - Events: `payment_intent.succeeded`, `payment_intent.payment_failed`

## 🛠️ Development

### Project Structure

- **Multi-file architecture**: Clear separation of concerns
- **Type safety**: Pydantic models for validation
- **Async/await**: Full async support with aiogram 3.x
- **Error handling**: Comprehensive error handling and logging
- **Production-ready**: Docker, CI/CD, logging, monitoring

### Adding New Features

1. **New Service:**
   - Add to `models/service.py` `SERVICES` dict
   - Update database slots

2. **New Handler:**
   - Add handler function in `bot/handlers.py`
   - Register in `register_handlers()`

3. **New Database Table:**
   - Create Pydantic model in `models/`
   - Add CRUD methods in `db/supabase_client.py`

## 📝 Edge Cases Handled

- ✅ **Double booking prevention**: Slot status checked before booking
- ✅ **Payment failures**: Booking can be cancelled if payment fails
- ✅ **No-shows**: Status tracking for completed/cancelled bookings
- ✅ **Slot conflicts**: Database constraints prevent overbooking
- ✅ **GDPR compliance**: Consent required before data processing

## 🔒 Security

- ✅ Environment variables for secrets
- ✅ Input validation with Pydantic
- ✅ Stripe webhook signature verification (implement in production)
- ✅ GDPR-compliant data handling
- ✅ No hardcoded credentials

## 📚 API Documentation

### Bot Commands

- `/start` - Start bot and show main menu

### Callback Data

- `book_appointment` - Start booking flow
- `service_{type}` - Select service
- `slot_{id}_{type}` - Select time slot
- `confirm_booking_{id}` - Confirm booking
- `payment_done_{id}` - Mark payment complete
- `my_bookings` - View user bookings
- `ask_question` - Start AI Q&A

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Contact: [your-email@example.com]

## 🎯 Roadmap

- [ ] SMS reminders (Twilio integration)
- [ ] Multi-language support
- [ ] Admin panel for slot management
- [ ] Customer reviews and ratings
- [ ] Recurring appointments
- [ ] Waitlist for popular slots

---

**Built with:** Python, aiogram 3.x, Supabase, Stripe, Claude AI, APScheduler, Playwright
