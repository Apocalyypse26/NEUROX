-- =============================================================================
-- Migration 0015: Credit System — Full Schema (user_profiles table + functions)
-- =============================================================================
-- This migration creates the user_profiles table (which was referenced in
-- previous migrations but never actually created in the live database),
-- sets up RLS policies, auto-provisioning trigger, and the consume_credit /
-- buy_credits RPC functions that the frontend calls during scan processing.
-- =============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create user_profiles table
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_profiles (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  credits     INTEGER     NOT NULL DEFAULT 10,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 2. Enable Row Level Security
-- ----------------------------------------------------------------------------
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can only read their own profile
CREATE POLICY IF NOT EXISTS "Users can view own profile"
ON public.user_profiles FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Users can update their own profile (credit deduction via RPC only)
CREATE POLICY IF NOT EXISTS "Users can update own profile"
ON public.user_profiles FOR UPDATE
TO authenticated
USING (auth.uid() = user_id);

-- Service role has full access (for admin operations)
CREATE POLICY IF NOT EXISTS "Service role full access"
ON public.user_profiles FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- 3. Auto-create profile row on new user signup
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.init_profile()
  RETURNS trigger
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = ''
AS $$
BEGIN
  INSERT INTO public.user_profiles (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Drop and recreate the trigger cleanly
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.init_profile();

-- ----------------------------------------------------------------------------
-- 4. Backfill profiles for any existing users (no-op if already exists)
-- ----------------------------------------------------------------------------
INSERT INTO public.user_profiles (user_id)
SELECT id FROM auth.users
ON CONFLICT (user_id) DO NOTHING;

-- Give all users at least 20 credits if they have the default 10 or less
UPDATE public.user_profiles
SET credits = 20
WHERE credits <= 10;

-- ----------------------------------------------------------------------------
-- 5. consume_credit() — uses auth.uid() internally (no client param needed)
--    Called by the frontend: supabase.rpc('consume_credit')
--    Returns true if a credit was consumed, false if insufficient credits
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.consume_credit()
  RETURNS boolean
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = ''
AS $function$
DECLARE
  credits_available INTEGER;
  calling_user      UUID;
BEGIN
  -- Resolve user from JWT — cannot be spoofed from the client
  calling_user := auth.uid();

  IF calling_user IS NULL THEN
    RETURN false;
  END IF;

  -- Lock the row to prevent race conditions on concurrent requests
  SELECT credits INTO credits_available
  FROM public.user_profiles
  WHERE user_profiles.user_id = calling_user
  FOR UPDATE;

  IF credits_available IS NULL OR credits_available <= 0 THEN
    RETURN false;
  END IF;

  UPDATE public.user_profiles
  SET credits = credits - 1
  WHERE user_profiles.user_id = calling_user;

  RETURN true;
END;
$function$;

-- ----------------------------------------------------------------------------
-- 6. buy_credits(amount) — adds credits to the calling user's account
--    Called server-side after payment confirmation
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.buy_credits(amount integer)
  RETURNS boolean
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = ''
AS $function$
DECLARE
  calling_user UUID;
BEGIN
  calling_user := auth.uid();

  IF calling_user IS NULL THEN
    RETURN false;
  END IF;

  UPDATE public.user_profiles
  SET credits = credits + amount
  WHERE user_profiles.user_id = calling_user;

  RETURN true;
END;
$function$;
