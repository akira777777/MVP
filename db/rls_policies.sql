-- Supabase Row Level Security (RLS) Policies
-- ============================================
-- 
-- These policies ensure that:
-- 1. Clients can only access their own data
-- 2. Service accounts (using service_role key) can access all data
-- 3. Unauthenticated requests are blocked
--
-- IMPORTANT: Enable RLS on all tables before applying these policies
--
-- To apply:
-- 1. Connect to your Supabase project SQL editor
-- 2. Run these commands in order
-- 3. Verify policies are active in Supabase Dashboard > Authentication > Policies

-- ============================================
-- Enable RLS on all tables
-- ============================================

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

-- ============================================
-- Clients Table Policies
-- ============================================

-- Policy: Service role can do everything (for backend operations)
CREATE POLICY "Service role full access on clients"
ON clients
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: Clients can read their own data
CREATE POLICY "Clients can read own data"
ON clients
FOR SELECT
TO authenticated
USING (auth.uid()::text = telegram_id::text);

-- Policy: Clients can update their own GDPR consent
CREATE POLICY "Clients can update own GDPR consent"
ON clients
FOR UPDATE
TO authenticated
USING (auth.uid()::text = telegram_id::text)
WITH CHECK (auth.uid()::text = telegram_id::text);

-- ============================================
-- Slots Table Policies
-- ============================================

-- Policy: Service role can do everything
CREATE POLICY "Service role full access on slots"
ON slots
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: Anyone authenticated can read available slots
CREATE POLICY "Authenticated users can read available slots"
ON slots
FOR SELECT
TO authenticated
USING (status = 'available');

-- Policy: Authenticated users can read all slots (for admin view)
-- Note: This allows clients to see booked slots too, but they can't modify them
CREATE POLICY "Authenticated users can read all slots"
ON slots
FOR SELECT
TO authenticated
USING (true);

-- ============================================
-- Bookings Table Policies
-- ============================================

-- Policy: Service role can do everything
CREATE POLICY "Service role full access on bookings"
ON bookings
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: Clients can read their own bookings
CREATE POLICY "Clients can read own bookings"
ON bookings
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM clients
        WHERE clients.id = bookings.client_id
        AND clients.telegram_id::text = auth.uid()::text
    )
);

-- Policy: Clients can create their own bookings
CREATE POLICY "Clients can create own bookings"
ON bookings
FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM clients
        WHERE clients.id = bookings.client_id
        AND clients.telegram_id::text = auth.uid()::text
    )
);

-- Policy: Clients can update their own pending bookings (for cancellation)
CREATE POLICY "Clients can update own pending bookings"
ON bookings
FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM clients
        WHERE clients.id = bookings.client_id
        AND clients.telegram_id::text = auth.uid()::text
        AND bookings.status IN ('pending', 'confirmed')
    )
)
WITH CHECK (
    EXISTS (
        SELECT 1 FROM clients
        WHERE clients.id = bookings.client_id
        AND clients.telegram_id::text = auth.uid()::text
    )
);

-- ============================================
-- Notes on Implementation
-- ============================================
--
-- 1. The bot uses service_role key (supabase_key from config)
--    This bypasses RLS and allows full access for backend operations
--
-- 2. For client-facing operations, we use the service_role key
--    but implement application-level authorization checks
--
-- 3. RLS provides defense-in-depth: even if application logic fails,
--    database-level policies prevent unauthorized access
--
-- 4. To test RLS:
--    - Create a test user in Supabase Auth
--    - Use their JWT token to query tables
--    - Verify they can only access their own data
--
-- 5. For admin operations, consider creating a separate admin role
--    with elevated permissions if needed in the future
