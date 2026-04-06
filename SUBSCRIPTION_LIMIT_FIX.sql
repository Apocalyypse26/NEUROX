-- =============================================================================
-- CRITICAL FIX: Subscription Scan Limit Enforcement
-- Copy and paste this into Supabase SQL Editor
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Add scans tracking column to user_subscriptions table
-- -----------------------------------------------------------------------------
ALTER TABLE public.user_subscriptions 
ADD COLUMN IF NOT EXISTS scans_used_this_month INTEGER DEFAULT 0;

-- -----------------------------------------------------------------------------
-- 2. Updated consume_credit() function with subscription enforcement
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.consume_credit()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  calling_user UUID;
  sub_record RECORD;
  credits_available INTEGER;
  monthly_limit INTEGER;
  scans_used INTEGER;
BEGIN
  calling_user := auth.uid();
  IF calling_user IS NULL THEN
    RETURN false;
  END IF;

  -- Check for unlimited subscription first
  SELECT scans_per_month, scans_used_this_month, is_unlimited 
  INTO sub_record
  FROM public.user_subscriptions
  WHERE user_id = calling_user 
    AND status = 'active'
    AND (current_period_end IS NULL OR current_period_end > NOW())
  LIMIT 1;

  -- UNLIMITED SUBSCRIPTION: Allow without credit check
  IF sub_record.is_unlimited = true THEN
    RETURN true;
  END IF;

  -- LIMITED SUBSCRIPTION: Check monthly scan limit
  IF sub_record.scans_per_month IS NOT NULL THEN
    monthly_limit := sub_record.scans_per_month;
    scans_used := COALESCE(sub_record.scans_used_this_month, 0);
    
    -- Reset if new month (simple approach: if used >= limit, allow one more then block)
    IF scans_used < monthly_limit THEN
      UPDATE public.user_subscriptions
      SET scans_used_this_month = scans_used + 1
      WHERE user_id = calling_user;
      RETURN true;
    ELSE
      RETURN false; -- Monthly limit exceeded
    END IF;
  END IF;

  -- NO SUBSCRIPTION: Check credits (original behavior)
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
$$;

-- -----------------------------------------------------------------------------
-- 3. Optional: Monthly reset function (can be called via cron job)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.reset_monthly_scans()
RETURNS void AS $$
BEGIN
  UPDATE public.user_subscriptions 
  SET scans_used_this_month = 0
  WHERE scans_used_this_month IS NOT NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;