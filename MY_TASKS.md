# Mohan Ramineni — My Backend Tasks (DineOS)

Notice: This folder contains a **full copy** of the `backend/` directory so the entire app can run and boot cleanly without missing dependency errors. However, you **only own and should only edit** your assigned module folder(s): `backend/app/modules/orders/`.

## Your tasks

### Order Management (POS)
- [ ] POS Cart
- [ ] Order Creation
- [ ] KOT Generation
- [ ] Order Status
- [ ] Order History

## Notes specific to you
- KOT generation and order status transitions live in orders' service code, not kds — coordinate closely with Navuluri Venkata Pardhasaradhi (KDS).

## Common responsibilities (everyone)
- [ ] Database Models
- [ ] Pydantic Schemas
- [ ] CRUD APIs
- [ ] Business Logic
- [ ] Validations
- [ ] Swagger Documentation
- [ ] Unit Testing
- [ ] Git Branch & Pull Request
- [ ] Code Review Fixes

## Running this locally
```bash
cd backend
pip install -r requirements.txt
# Configure .env (already pre-configured in this directory)
alembic upgrade head
uvicorn app.main:app --reload
```
Interactive Swagger API Documentation: http://127.0.0.1:8000/docs

## Git workflow
Suggested branch name: `feature/mohan-ramineni-orders`

Reminder: Only touch your own assigned module folder(s) in your PR to avoid merge conflicts with teammates editing shared files.