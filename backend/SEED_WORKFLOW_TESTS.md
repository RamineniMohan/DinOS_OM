# DineOS Demo Seed — Workflow Test Guide

This file lists the **exact API calls** to make against a server loaded with `seed_demo.py` data.
Run the seed script first, then copy the `ID` values from its printed summary into the calls below.

> **Base URL**: `http://127.0.0.1:8000/api/v1`
> **Auth header**: `Authorization: Bearer <access_token>` (obtain via Login step below)

---

## 0. Get Your Token

```
POST /auth/login
{
  "email": "owner@spiceroute.demo",
  "password": "Password123!"
}
→ copy access_token from response
```

---

## 1. Authentication Module

| Action | Call |
|---|---|
| Login as manager | `POST /auth/login` `{"email":"manager@spiceroute.demo","password":"Password123!"}` |
| Login as cashier | `POST /auth/login` `{"email":"cashier@spiceroute.demo","password":"Password123!"}` |
| Login as super_admin | `POST /auth/login` `{"email":"superadmin@dineos.demo","password":"Password123!"}` |
| Verify active sessions | `GET /auth/sessions` |
| Logout current session | `POST /auth/logout` |
| MFA setup (optional) | `POST /auth/mfa/setup` |
| Password reset flow | `POST /auth/password-reset/request` `{"email":"cashier@spiceroute.demo"}` → then `POST /auth/password-reset/reset` with OTP |

---

## 2. Tenancy & Branch Management

```
GET  /tenancy/restaurants             → list all restaurants (super_admin)
GET  /tenancy/branches                → list branches for your tenant
PATCH /tenancy/restaurants/{restaurant_id}
     {"name": "Spice Route Premium", "city": "Mumbai"}
POST /tenancy/branches
     {"name": "Airport Terminal 3", "address": "IGI Airport, New Delhi"}
```

---

## 3. Menu Management

```
# Add a new category
POST /menu/categories
     {"name": "Chef's Special", "description": "Seasonal specials", "sort_order": 5}

# Update an item's price
PATCH /menu/items/{butter_chicken_item_id}
     {"base_price": 400}

# Add a new variant to an existing item
POST /menu/variants
     {"menu_item_id": "{paneer_tikka_id}", "name": "Party Pack", "price": 650}

# Test branch price override — Mall Road sees ₹390 for Butter Chicken
GET /menu/items?branch_id={mall_road_branch_id}
```

---

## 4. Operations (Tables & Floors)

```
# List all tables for Main Street branch
GET /operations/tables?branch_id={main_street_branch_id}

# Mark a table as occupied
PATCH /operations/tables/{table_id}
     {"is_occupied": true}

# Add a new floor to a branch
POST /operations/floors
     {"branch_id": "{branch_id}", "name": "Rooftop Terrace"}
```

---

## 5. Order Management — Advance the State Machine

### 5a. Move the PLACED order forward

```
# Confirm the placed order
PATCH /orders/{placed_order_id}/status
     {"status": "confirmed"}

# Kitchen starts preparing
PATCH /orders/{placed_order_id}/status
     {"status": "preparing"}

# Food is ready
PATCH /orders/{placed_order_id}/status
     {"status": "ready"}

# Order served — this triggers inventory auto-deduction!
PATCH /orders/{placed_order_id}/status
     {"status": "served"}
```

### 5b. Create a brand-new order (test POS cart)

```
POST /orders
{
  "branch_id": "{main_street_branch_id}",
  "order_type": "dine_in",
  "table_id": "{table_id}",
  "customer_name": "New Walk-in",
  "customer_phone": "+919000000001",
  "items": [
    {
      "menu_item_id": "{gulab_jamun_item_id}",
      "item_name": "Gulab Jamun (2 pcs)",
      "quantity": 2,
      "unit_price": 110,
      "addons": []
    }
  ],
  "idempotency_key": "test-order-001"
}
```

---

## 6. Kitchen Display System (KDS)

```
# Connect the KDS WebSocket for Main Street branch
WS ws://127.0.0.1:8000/api/v1/kds/ws/{main_street_branch_id}
→ Each status PATCH on an order pushes a live JSON event here

# List current KDS tickets
GET /kds/tickets?branch_id={main_street_branch_id}
```

---

## 7. Billing

### 7a. Complete the partial payment on the existing invoice

```
# Find the invoice first
GET /billing/invoices/{invoice_id}
→ payment_status = "partially_paid"

# Pay the remaining balance
POST /billing/payments
{
  "invoice_id": "{invoice_id}",
  "amount": <remaining_balance>,
  "method": "cash"
}
→ invoice payment_status should now be "paid"
→ loyalty points (10% of total) are auto-accrued to Rohit Mehta
```

### 7b. Generate invoice for the PLACED → SERVED order (after advancing it in step 5)

```
POST /billing/invoices
{
  "order_id": "{placed_order_id}",
  "customer_name": "Anjali Nair",
  "customer_phone": "+919123456789"
}
→ Verify CGST + SGST split in response (intra-state Delhi)
```

### 7c. Test a refund

```
POST /billing/refunds
{
  "payment_id": "{payment_id}",
  "amount": 100,
  "reason": "Customer complained about quality"
}
```

---

## 8. CRM & Loyalty

### 8a. Redeem existing points (Rohit Mehta has 250 pts)

```
POST /crm/loyalty/redeem
{
  "customer_id": "{rohit_mehta_customer_id}",
  "points_to_redeem": 100,
  "order_id": "{placed_order_id}"
}
→ Returns discount_amount: 50.0 (1 pt = ₹0.50)
→ Rohit's balance drops from 250 → 150
```

### 8b. Lookup or create a customer by phone

```
POST /crm/customers/lookup
{
  "phone": "+919000099999",
  "name": "New Customer",
  "email": "new@test.com"
}
```

### 8c. Submit feedback (public — no auth needed, just restaurant_id)

```
POST /crm/feedback?restaurant_id={restaurant_id}
{
  "order_id": "{any_served_order_id}",
  "rating": 4,
  "comments": "Great food, slightly long wait"
}
```

---

## 9. Inventory Management

### 9a. Restock the near-threshold ingredient (Saffron)

```
POST /inventory/adjust
{
  "ingredient_id": "{saffron_ingredient_id}",
  "quantity_change": 50,
  "reason": "purchase",
  "notes": "Weekly restock from supplier"
}
→ Saffron stock: 10g → 60g (well above threshold)
```

### 9b. Check low-stock alerts

```
GET /inventory/ingredients?low_stock=true
→ Should return Saffron (before restock) with current_stock ≤ low_stock_threshold
```

### 9c. Add a new ingredient and link it to a recipe

```
POST /inventory/ingredients
{"name": "Butter", "unit": "kg", "current_stock": 5.0, "low_stock_threshold": 1.0}

PATCH /inventory/recipes/{recipe_id}
{"ingredients": [..., {"ingredient_id": "{butter_id}", "quantity": 0.05}]}
```

---

## 10. Reports & Analytics

```
# Sales report for today
GET /reports/sales?start_date=2026-07-19&end_date=2026-07-19

# GST report (GSTR-1 format)
GET /reports/gst?start_date=2026-07-01&end_date=2026-07-31

# Inventory levels report
GET /reports/inventory

# Export as Excel
GET /reports/sales/export?format=xlsx&start_date=2026-07-01&end_date=2026-07-31

# Export as PDF
GET /reports/sales/export?format=pdf&start_date=2026-07-01&end_date=2026-07-31
```

---

## 11. Subscriptions

```
# List available plans
GET /subscriptions/plans

# View current restaurant subscription
GET /subscriptions/current

# Simulate Razorpay checkout (returns payment link)
POST /subscriptions/checkout
{"plan_id": "{pro_monthly_plan_id}", "interval": "monthly"}
```

---

## 12. System — Audit Logs

```
# View all audit log entries for the restaurant (owner/super_admin only)
GET /system/audit-logs?limit=50
→ Shows every DB INSERT/UPDATE/DELETE with user + IP context
```

---

## Quick Copy-Paste: Full Happy Path (5 minutes)

```bash
# 1. Login
curl -X POST /auth/login -d '{"email":"owner@spiceroute.demo","password":"Password123!"}'

# 2. Confirm → Preparing → Ready → Served (advances placed order)
curl -X PATCH /orders/{placed_order_id}/status -d '{"status":"confirmed"}'
curl -X PATCH /orders/{placed_order_id}/status -d '{"status":"preparing"}'
curl -X PATCH /orders/{placed_order_id}/status -d '{"status":"ready"}'
curl -X PATCH /orders/{placed_order_id}/status -d '{"status":"served"}'

# 3. Generate invoice
curl -X POST /billing/invoices -d '{"order_id":"{placed_order_id}"}'

# 4. Complete partial payment
curl -X POST /billing/payments -d '{"invoice_id":"{invoice_id}","amount":<remaining>,"method":"upi"}'

# 5. Redeem loyalty points
curl -X POST /crm/loyalty/redeem -d '{"customer_id":"{rohit_id}","points_to_redeem":100}'

# 6. Restock saffron
curl -X POST /inventory/adjust -d '{"ingredient_id":"{saffron_id}","quantity_change":50,"reason":"purchase"}'

# 7. Export GST report
curl -X GET '/reports/gst?start_date=2026-07-01&end_date=2026-07-31&format=xlsx'
```
