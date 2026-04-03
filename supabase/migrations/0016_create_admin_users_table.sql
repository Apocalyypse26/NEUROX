-- Create admin_users table for managing admin access
-- This table should only be accessible via service role key

-- Create the table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.admin_users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  admin_role TEXT DEFAULT 'admin' CHECK (admin_role IN ('admin', 'super_admin')),
  is_active BOOLEAN DEFAULT true
);

-- Enable RLS
ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any
DROP POLICY IF EXISTS "Service role can manage admin_users" ON public.admin_users;
DROP POLICY IF EXISTS "Admins can view admin_users" ON public.admin_users;

-- Create strict RLS policies
-- Only service role can SELECT (backend uses this)
CREATE POLICY "Service role can manage admin_users"
ON public.admin_users FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Public read access is denied (security by default)
CREATE POLICY "Deny public read access"
ON public.admin_users FOR SELECT
TO authenticated
USING (false);

-- Comments for documentation
COMMENT ON TABLE public.admin_users IS 'Stores admin user IDs with their roles. Only service role key should access this table.';
COMMENT ON COLUMN public.admin_users.id IS 'References auth.users.id - the admin user ID';
COMMENT ON COLUMN public.admin_users.admin_role IS 'Admin role type: admin or super_admin';
COMMENT ON COLUMN public.admin_users.is_active IS 'Whether this admin account is active';

-- Add some helpful notes
-- To add an admin, use Supabase Dashboard > Table Editor > admin_users > Insert
-- Or run: INSERT INTO public.admin_users (id) VALUES ('your-user-uuid');
