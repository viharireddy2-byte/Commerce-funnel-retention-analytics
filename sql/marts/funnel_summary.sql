SELECT device_category, traffic_medium,
SUM(has_viewed) visitors, SUM(has_added_to_cart) cart_adders, SUM(has_checkout) checkout_starters,
SUM(has_purchased) purchasers, SUM(purchase_revenue) total_revenue,
SUM(has_added_to_cart)*1.0/NULLIF(SUM(has_viewed),0) visitor_to_cart_rate,
SUM(has_checkout)*1.0/NULLIF(SUM(has_added_to_cart),0) cart_to_checkout_rate,
SUM(has_purchased)*1.0/NULLIF(SUM(has_checkout),0) checkout_to_purchase_rate,
SUM(has_purchased)*1.0/NULLIF(SUM(has_viewed),0) overall_conversion_rate
FROM int_funnel_stages GROUP BY 1,2
