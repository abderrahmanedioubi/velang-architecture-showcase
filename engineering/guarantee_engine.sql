-- engineering/guarantee_engine.sql
-- Velang Showcase: System Integrity & Revenue Protection Logic

/**
 * ARCHITECTURAL OVERVIEW:
 * 
 * The "Financial Guarantee" is the core value proposition of Velang. To prevent manipulation
 * and ensure pedagogical adherence, the verification logic is enforced at the DATABASE layer.
 * 
 * Key Features Demonstrated:
 * 1. Server-Side Target Locking: Prevents client-side manipulation of daily goals.
 * 2. Anti-Gaming Heuristics: A 10-second quality threshold (Telemetry-based).
 * 3. Atomic State Management: Deterministic transitions between ACTIVE, GRACE, and VOID.
 */

-- 1. DAILY TARGET INITIALIZATION (Server-Side Source of Truth)
CREATE OR REPLACE FUNCTION public.initialize_daily_guarantee(
    p_user_id UUID,
    p_date DATE,
    p_new_cards_target INTEGER DEFAULT 15
)
RETURNS void AS $$
DECLARE
    v_server_reviews_due INTEGER;
    v_tz TEXT;
BEGIN
    -- Get user's timezone to calculate "End of Day"
    SELECT timezone INTO v_tz FROM public.users WHERE id = p_user_id;
    
    -- Count actual reviews due at this moment (Immutable server-side count)
    -- This prevents users from manually reducing their "due" count to trick the system.
    SELECT count(id) INTO v_server_reviews_due
    FROM public.user_card_progress
    WHERE user_id = p_user_id
      AND due <= (p_date + 1 + interval '4 hours') AT TIME ZONE COALESCE(v_tz, 'UTC');

    INSERT INTO public.guarantee_tracking (
        user_id, date, status, reviews_due, new_cards_target
    )
    VALUES (
        p_user_id, p_date, 'PENDING', v_server_reviews_due, p_new_cards_target
    )
    ON CONFLICT (user_id, date) DO NOTHING;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 2. BATCHED GUARANTEE EVALUATION (The "Arbiter" Function)
CREATE OR REPLACE FUNCTION public.evaluate_daily_guarantees_batched(
    p_batch_size INT DEFAULT 100
)
RETURNS INT AS $$
DECLARE
    v_count INT := 0;
    t RECORD;
BEGIN
    -- This cron-triggered function evaluates yesterday's performance for all active users.
    FOR t IN 
        SELECT tracking.*, u.grace_days, u.timezone
        FROM public.guarantee_tracking tracking
        JOIN public.users u ON tracking.user_id = u.id
        WHERE tracking.status = 'PENDING'
          AND u.guarantee_status = 'ACTIVE'
          -- Evaluate based on the user's local "Yesterday"
          AND tracking.date = (now() AT TIME ZONE COALESCE(u.timezone, 'UTC') - INTERVAL '4 hours')::date - 1
        LIMIT p_batch_size
    LOOP
        -- CRITERIA 1: Completion (90% Threshold)
        -- CRITERIA 2: Quality (Min 10 seconds per card average to prevent speed-clicking)
        IF (
            (COALESCE(t.reviews_completed, 0) + COALESCE(t.new_cards_completed, 0)) >= 
            (0.9 * (COALESCE(t.reviews_due, 0) + COALESCE(t.new_cards_target, 0)))
        ) AND (
            (COALESCE(t.time_spent_seconds, 0)::FLOAT / 
             NULLIF(COALESCE(t.reviews_completed, 0) + COALESCE(t.new_cards_completed, 0), 0) >= 10)
        ) THEN
            UPDATE public.guarantee_tracking SET status = 'SUCCESS' WHERE user_id = t.user_id AND date = t.date;
        ELSE
            -- Handle failure via the Grace system
            IF t.grace_days > 0 THEN
                UPDATE public.guarantee_tracking SET status = 'GRACE_USED' WHERE user_id = t.user_id AND date = t.date;
                UPDATE public.users SET grace_days = grace_days - 1 WHERE id = t.user_id;
            ELSE
                UPDATE public.guarantee_tracking SET status = 'FAILED' WHERE user_id = t.user_id AND date = t.date;
                UPDATE public.users SET guarantee_status = 'VOIDED' WHERE id = t.user_id;
            END IF;
        END IF;
        
        v_count := v_count + 1;
    END LOOP;

    RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
