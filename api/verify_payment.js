const { createClient } = require('@supabase/supabase-js');

/**
 * Velang Payment Verification Webhook (SlickPay Integration)
 * 
 * This endpoint is responsible for:
 * 1. Validating the payment status with the SlickPay API.
 * 2. Updating the user's payment status in the 'users' table.
 * 3. Initializing the "Financial Guarantee" tracking for the user.
 * 
 * ARCHITECTURAL NOTE: This demonstrates a secure, server-side fulfillment 
 * pattern that prevents client-side manipulation of premium access.
 */
async function verifyPayment(req, res) {
  const { invoiceId } = req.body;

  if (!invoiceId) {
    return res.status(400).json({ error: "Missing invoiceId parameter." });
  }

  // Configuration (Replace with your actual environment variables in production)
  const SLICKPAY_PUBLIC_KEY = process.env.SLICKPAY_PUBLIC_KEY;
  const SLICKPAY_BASE_URL = process.env.NODE_ENV === "production"
    ? "https://prodapi.slick-pay.com/api/v2"
    : "https://devapi.slick-pay.com/api/v2";

  try {
    // 1. Verify payment status directly with the SlickPay API (Secondary Validation)
    const verifyRes = await fetch(`${SLICKPAY_BASE_URL}/users/invoices/${invoiceId}`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "Authorization": `Bearer ${SLICKPAY_PUBLIC_KEY}`,
      }
    });

    const verifyJson = await verifyRes.json();
    const paymentStatus = verifyJson.data?.status;
    const isPaid = (paymentStatus === 1 || paymentStatus === 'completed' || paymentStatus === 'paid');

    // 2. Administrative Supabase Client
    const supabase = createClient(
      process.env.SUPABASE_URL || "YOUR_SUPABASE_URL_HERE",
      process.env.SUPABASE_SERVICE_ROLE_KEY || "YOUR_SERVICE_ROLE_KEY_HERE"
    );

    // 3. Fetch transaction and verify its current state
    const { data: trx, error: trxError } = await supabase
      .from('transactions')
      .select('*')
      .eq('invoice_id', invoiceId)
      .single();

    if (trxError || !trx) throw new Error("Transaction record not found.");

    // 4. Atomic Fulfillment Lifecycle
    if (isPaid && trx.status === 'pending') {
      
      // Update transaction status
      await supabase
        .from('transactions')
        .update({ status: 'completed' })
        .eq('id', trx.id);
        
      // Upgrade User Account (Unified Schema Pattern)
      const { error: userError } = await supabase
        .from('users')
        .update({ 
          payment_status: 'PREMIUM', 
          selected_tier: trx.selected_tier,
          guarantee_status: 'ACTIVE' // Activate the Financial Guarantee
        })
        .eq('id', trx.user_id);

      if (userError) throw new Error("Failed to provision user access.");

      // 5. Initialize Financial Guarantee (Server-Side Logic)
      // We trigger the DB function to lock the first day's targets.
      const today = new Date().toISOString().split('T')[0];
      const { error: rpcError } = await supabase.rpc('initialize_daily_guarantee', {
        p_user_id: trx.user_id,
        p_date: today,
        p_new_cards_target: 15 // Default intensity
      });

      if (rpcError) console.warn("Guarantee tracking initialization failed, but payment was successful.");

      return res.status(200).json({ 
        status: "success", 
        message: "Account upgraded and guarantee initialized." 
      });
    }

    return res.status(200).json({ status: "pending", message: "Verification ongoing." });

  } catch (err) {
    console.error("Critical Fulfillment Error:", err.message);
    return res.status(500).json({ error: "Internal processing error." });
  }
}

module.exports = { verifyPayment };
