# Idempotent Purchases

A Flask backend that sells limited-stock items under heavy concurrent load,
guaranteeing that a single logical purchase attempt — even if retried
multiple times due to network failure — is applied **exactly once**, and
that stock is **never oversold**, no matter how many requests arrive at
the same instant.

## The Problem

Two hard concurrency problems, solved together:

1. **Overselling** — many requests may try to buy the last unit(s) of a
   product at the same instant. The system must never sell more stock
   than exists.
2. **Duplicate purchases from retries** — a client may send the same
   purchase request more than once (e.g. it never received the response
   to its first attempt due to a network failure). A retry must have
   **no additional effect** — no double stock decrement, no duplicate
   order — while still returning the correct result.

## How It Works

Each purchase request includes a client-generated **idempotency key**
(a UUID). The endpoint:

1. Attempts to **insert** a row into `idempotency_key` using that key as
   the primary key. This insert is the atomic "claim" on the key — if
   two requests with the same key arrive at the same instant, the
   database's own uniqueness guarantee ensures only one insert can ever
   succeed. The other fails immediately with an integrity error and is
   treated as a duplicate.
2. If the claim succeeds, the request locks the relevant `product` row
   with `SELECT ... FOR UPDATE`, serializing concurrent stock checks
   against that specific product so two requests can never both read
   and decrement the same stock count.
3. If stock is available, it decrements stock, creates an `order`, and
   marks the idempotency key `Successfull` with a reference to the new
   order. If stock is unavailable, the key is marked `Out of Stock`.
4. All of the above happens inside a **single transaction**, so a crash
   or error partway through rolls back the claim along with everything
   else — no key is ever left permanently stuck mid-processing.
5. A retry with the same key hits the failed insert, looks up the
   already-stored outcome, and returns it directly — without
   re-running any purchase logic.

## Endpoints

- `POST /products` — create a product with initial stock
- `POST /purchase` — attempt a purchase, given a `product_id` and an
  `idempotent_key`

## Tech Stack

Flask, Flask-SQLAlchemy, SQLite (Postgres planned), Gunicorn, Redis
(available for future caching use).

## Testing

`test.py` fires the API under real concurrent load using
`ThreadPoolExecutor` and checks the properties above hold under
adversarial conditions rather than just the happy path:

- Same key fired 500 times concurrently → exactly one order created
- Same key retried sequentially 20 times → identical result returned
  each time
- 500 unique keys competing for 10 units of stock → never more than 10
  successful purchases
- 500 unique keys competing for a **single** unit of stock → exactly
  one winner, repeated across 20 rounds
- Multiple products purchased concurrently → no cross-contamination
  between products' stock counts

All tests pass consistently against the current implementation.

## Known Limitations / Next Steps

- Currently runs on SQLite, which serializes all writes at the
  database level; a Postgres migration is planned to allow genuine
  concurrent writes across different rows and support meaningfully
  higher throughput.
- No authentication on purchase requests yet.
- Redis is installed but not yet used for caching product reads.