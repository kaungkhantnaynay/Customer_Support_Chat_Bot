# BeanCo Payments And Cancellations

BeanCo checkout uses Stripe-hosted payment pages for Thai baht card and PromptPay payments. BeanCo does not receive or store raw payment credentials.

Customers can retry payment from an awaiting-payment order. If a payment session expires or fails, the order is cancelled and reserved stock is released.

A signed-in customer can cancel an awaiting-payment order from the order details page. A confirmed order can be cancelled for a full refund only before fulfillment begins.

Refunds are returned through Stripe to the original payment method. Support must escalate duplicate charges, failed refunds, disputed payments, paid orders that appear cancelled, and any request that requires inspecting a customer's payment or order record.
