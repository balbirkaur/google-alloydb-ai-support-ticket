INSERT INTO support_tickets (description, issue_type, status, priority, embedding)
VALUES
(
 'Payment failed during checkout',
 'Payment',
 'Open',
 'High',
 embedding('text-embedding-005', 'Payment failed during checkout')::vector
),
(
 'Unable to login to account',
 'Login',
 'Closed',
 'Medium',
 embedding('text-embedding-005', 'Unable to login to account')::vector
),
(
 'Order delivery delayed',
 'Delivery',
 'Open',
 'High',
 embedding('text-embedding-005', 'Order delivery delayed')::vector
);