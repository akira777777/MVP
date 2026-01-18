# Database ERD (Entity Relationship Diagram)

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLIENTS                             │
├─────────────────────────────────────────────────────────────┤
│ PK │ id                    │ UUID                           │
│    │ telegram_id           │ BIGINT (UNIQUE)                │
│    │ first_name            │ TEXT (NOT NULL)                │
│    │ last_name             │ TEXT                            │
│    │ username              │ TEXT                            │
│    │ phone                 │ TEXT                            │
│    │ email                 │ TEXT                            │
│    │ gdpr_consent          │ BOOLEAN (DEFAULT FALSE)         │
│    │ gdpr_consent_date     │ TIMESTAMPTZ                     │
│    │ created_at            │ TIMESTAMPTZ (DEFAULT NOW)        │
│    │ updated_at            │ TIMESTAMPTZ (DEFAULT NOW)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 1
                              │
                              │ has many
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BOOKINGS                              │
├─────────────────────────────────────────────────────────────┤
│ PK │ id                    │ UUID                            │
│ FK │ client_id             │ UUID → clients.id               │
│ FK │ slot_id               │ UUID → slots.id                 │
│    │ service_type          │ TEXT (NOT NULL)                 │
│    │ status                │ TEXT (CHECK: pending/confirmed/ │
│    │                       │        paid/cancelled/completed/ │
│    │                       │        no_show)                 │
│    │ price_czk             │ INTEGER (NOT NULL)              │
│    │ stripe_payment_intent │ TEXT                            │
│    │ stripe_payment_status │ TEXT                            │
│    │ reminder_sent         │ BOOLEAN (DEFAULT FALSE)         │
│    │ reminder_sent_at      │ TIMESTAMPTZ                     │
│    │ notes                 │ TEXT                            │
│    │ created_at            │ TIMESTAMPTZ (DEFAULT NOW)       │
│    │ updated_at            │ TIMESTAMPTZ (DEFAULT NOW)       │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │
                              │ belongs to
                              │
                              │ 1
                              │
┌─────────────────────────────────────────────────────────────┐
│                          SLOTS                              │
├─────────────────────────────────────────────────────────────┤
│ PK │ id                    │ UUID                            │
│    │ start_time            │ TIMESTAMPTZ (NOT NULL)          │
│    │ end_time              │ TIMESTAMPTZ (NOT NULL)          │
│    │ status                │ TEXT (CHECK: available/booked/  │
│    │                       │        cancelled/completed)    │
│    │ service_type          │ TEXT (NOT NULL)                 │
│    │ created_at            │ TIMESTAMPTZ (DEFAULT NOW)        │
│    │ updated_at            │ TIMESTAMPTZ (DEFAULT NOW)       │
└─────────────────────────────────────────────────────────────┘
```

## Relationships

### Clients → Bookings (1:N)
- One client can have many bookings
- Foreign key: `bookings.client_id` → `clients.id`
- Cascade delete: If client is deleted, bookings are deleted

### Slots → Bookings (1:N)
- One slot can have one booking (enforced by status)
- Foreign key: `bookings.slot_id` → `slots.id`
- Cascade delete: If slot is deleted, bookings are deleted

## Indexes

```sql
-- Performance indexes
CREATE INDEX idx_clients_telegram_id ON clients(telegram_id);
CREATE INDEX idx_slots_service_status ON slots(service_type, status);
CREATE INDEX idx_slots_start_time ON slots(start_time);
CREATE INDEX idx_bookings_client_id ON bookings(client_id);
CREATE INDEX idx_bookings_slot_id ON bookings(slot_id);
CREATE INDEX idx_bookings_status ON bookings(status);
```

## Constraints

### Clients
- `telegram_id` must be unique
- `first_name` is required

### Slots
- `start_time` < `end_time` (application-level check)
- `status` must be one of: available, booked, cancelled, completed
- `service_type` must match available services

### Bookings
- `status` must be one of: pending, confirmed, paid, cancelled, completed, no_show
- `price_czk` must be >= 0
- `client_id` must reference existing client
- `slot_id` must reference existing slot

## Business Rules

1. **Slot Availability**: A slot can only be booked if `status = 'available'`
2. **Double Booking Prevention**: When booking is created, slot status changes to `booked`
3. **Payment Flow**: Booking starts as `pending`, becomes `paid` after Stripe confirmation
4. **Reminders**: Only sent for `confirmed` or `paid` bookings that haven't received reminder
5. **GDPR**: Client must consent before any booking can be created

## Data Flow

### Booking Creation
1. Client selects service and slot
2. Booking created with `status = 'pending'`
3. Slot `status` changed to `booked`
4. Stripe PaymentIntent created
5. On payment success: Booking `status = 'paid'`

### Reminder Process
1. Scheduler checks bookings where:
   - `status IN ('confirmed', 'paid')`
   - `reminder_sent = FALSE`
   - Slot `start_time` is within reminder window (24h)
2. Reminder sent via Telegram
3. Booking `reminder_sent = TRUE`, `reminder_sent_at` set

### Cancellation
1. Booking `status = 'cancelled'`
2. Slot `status = 'available'` (freed up)
3. Payment refunded if already paid (Stripe)

## Sample Queries

### Get available slots for service
```sql
SELECT * FROM slots
WHERE service_type = 'manicure'
  AND status = 'available'
  AND start_time >= NOW()
ORDER BY start_time ASC;
```

### Get client bookings
```sql
SELECT b.*, s.start_time, s.end_time
FROM bookings b
JOIN slots s ON b.slot_id = s.id
WHERE b.client_id = $1
ORDER BY s.start_time DESC;
```

### Get bookings needing reminders
```sql
SELECT b.*, s.start_time, c.telegram_id
FROM bookings b
JOIN slots s ON b.slot_id = s.id
JOIN clients c ON b.client_id = c.id
WHERE b.status IN ('confirmed', 'paid')
  AND b.reminder_sent = FALSE
  AND s.start_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours';
```
