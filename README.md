<<<<<<< HEAD
# Restaurant POS - Order Management API

A Restaurant POS Order Management System built using FastAPI, SQLAlchemy Async, and PostgreSQL.

---

## Features

- POS Cart
- Order Creation
- Order Number Generation
- KOT Generation
- Kitchen Order Management
- Order Status
- Order History
- Repository Pattern
- Service Layer
- PostgreSQL
- Async SQLAlchemy

---

## Project Structure

```
app/
│
├── api/
├── core/
├── database/
├── models/
├── repositories/
├── schemas/
├── services/
├── utils/
└── main.py
```

---

## Installation

Create virtual environment

```bash
python -m venv .venv
```

Activate

Windows

```bash
.venv\Scripts\activate
```

Linux / Mac

```bash
source .venv/bin/activate
```

Install packages

```bash
pip install -r requirements.txt
```

---

## Configure Environment

Update the `.env` file.

Example

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_pos

SECRET_KEY=your_secret_key
```

---

## Run Server

```bash
uvicorn app.main:app --reload
```

---

## Swagger

```
http://127.0.0.1:8000/docs
```

---

## ReDoc

```
http://127.0.0.1:8000/redoc
```

---

## Modules

### Cart

- Create Cart
- Add Item
- Remove Item
- Update Quantity

### Order

- Create Order
- Update Status
- Cancel Order

### KOT

- Generate KOT
- Kitchen Workflow

### History

- Completed Orders
- Cancelled Orders

### Status

- Pending
- Confirmed
- Preparing
- Ready
- Served
- Completed

---

## Technology Stack

- FastAPI
- SQLAlchemy Async
- PostgreSQL
- Pydantic V2
- Repository Pattern
- Service Layer

---

## Author

Restaurant POS Backend
=======
# DinOS_OM
>>>>>>> 15937eacc58ea853fc9e89ad30c9c01fafef453b
