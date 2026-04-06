const { createClient } = require('@supabase/supabase-js');

/**
 * Velang Payment Verification Webhook (SlickPay Integration)
 * 
 * This endpoint is responsible for:
 * 1. Validating the payment status with the SlickPay API.
 * 2. Cross-referencing the transaction in our Supabase database.
 * 3. Atomically upgrading the user to Premium status upon successful verification.
 */
async function verifyPayment(req, res) {
  const { invoiceId } = req.body;

  if (!invoiceId) {
    return res.status(400).json({ error: "Missing invoiceId parameter." });
  }

  // Configuration (Replace with your actual environment variables in production)
  const SLICKPAY_PUBLIC_KEY = process.env.SLICKPAY_PUBLIC_KEY || "YOUR_SLICKPAY_KEY_HERE";
  const SLICKPAY_BASE_URL = process.env.NODE_ENV === "production"
    ? "https://prodapi.slick-pay.com/api/v2"
    : "https://devapi.slick-pay.com/api/v2";

  try {
    // 1. Verify payment status directly with the SlickPay API
    // This provides a secondary layer of security over client-side callbacks.
    const verifyRes = await fetch(`${SLICKPAY_BASE_URL}/users/invoices/${invoiceId}`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "Authorization": `Bearer ${SLICKPAY_PUBLIC_KEY}`,
      }
    });

    const verifyJson = await verifyRes.json();
    if (verifyJson.errors) {
      console.error("SlickPay Verification Error:", verifyJson.errors);
      throw new Error("Unable to verify invoice with payment gateway.");
    }

    const paymentStatus = verifyJson.data?.status;
    const isPaid = (paymentStatus === 1 || paymentStatus === 'completed' || paymentStatus === 'paid');

    // 2. Connect to Supabase using a Service Role key for administrative actions
    const supabase = createClient(
      process.env.SUPABASE_URL || "YOUR_SUPABASE_URL_HERE",
      process.env.SUPABASE_SERVICE_ROLE_KEY || "YOUR_SERVICE_ROLE_KEY_HERE"
    );

    // 3. Fetch the local transaction record
    const { data: trx, error: trxError } = await supabase
      .from('transactions')
      .select('*')
      .eq('invoice_id', invoiceId)
      .single();

    if (trxError || !trx) {
      throw new Error("Transaction record not found in database.");
    }

    // 4. Update Transaction and Upgrade User Profile
    if (isPaid && trx.status === 'pending') {
      
      // Update local transaction status
      await supabase
        .from('transactions')
        .update({ status: 'completed' })
        .eq('id', trx.id);
        
      // Provision Premium access to the user
      const { error: profileError } = await supabase
        .from('profiles')
        .update({ 
          is_premium: true, 
          premium_plan: trx.target_plan,
          premium_expires_at: trx.target_plan === 'lifetime' 
            ? null 
            : new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
        })
        .eq('id', trx.user_id);

      if (profileError) {
        throw new Error("Payment verified, but failed to provision user access.");
      }

      return res.status(200).json({ 
        status: "success", 
        message: "Payment verified successfully. User access granted." 
      });
    }

    return res.status(200).json({ 
      status: "pending", 
      message: "Payment is still processing or has already been fulfilled." 
    });

  } catch (err) {
    console.error("Verification Lifecycle Error:", err.message);
    return res.status(500).json({ error: "An internal error occurred during verification." });
  }
}

module.exports = { verifyPayment };
