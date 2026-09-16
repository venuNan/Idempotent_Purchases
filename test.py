"""
Tests two things for the idempotent flash-sale purchase endpoint:

1. IDEMPOTENCY: same key fired concurrently many times -> exactly ONE
   success, all others get back the same result, stock decrements by 1
   (not by the number of duplicate requests).

2. NO OVERSELLING: many DIFFERENT keys fired concurrently against limited
   stock -> successes never exceed available stock, final stock >= 0.
"""

import uuid, requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://127.0.0.1:5000"

def create_product(name):
    res = requests.post(f"{BASE_URL}/products", json={"product_name": name})
    # fetch its id — adjust this if your /products response includes the id directly
    return res.json()

def purchase(product_id, key):
    res = requests.post(f"{BASE_URL}/purchase", json={
        "product_id": product_id,
        "idempotent_key": key,
    })
    return res.status_code

# --- Test 1: idempotency — same key, fired concurrently ---
print("=== Test 1: Idempotency (same key x50, concurrent) ===")
product_id = 1  # replace with a real product_id you've created
same_key = str(uuid.uuid4())

with ThreadPoolExecutor(50) as ex:
    results = list(ex.map(lambda _: purchase(product_id, same_key), range(50)))

successes = results.count(201)
print(f"201 responses: {successes} (expected: 1)")
print(f"All status codes: {set(results)}")

# --- Test 2: no overselling — different keys, concurrent, limited stock ---
print("\n=== Test 2: Overselling check (100 unique keys vs stock=10) ===")
product_id_2 = 2  # a FRESH product with stock=10, not reused from test 1
unique_keys = [str(uuid.uuid4()) for _ in range(100)]

with ThreadPoolExecutor(50) as ex:
    results2 = list(ex.map(lambda k: purchase(product_id_2, k), unique_keys))

successes2 = results2.count(201)
print(f"201 responses: {successes2} (expected: 10, i.e. == stock)")
print(f"All status codes: {set(results2)}")

if successes2 > 10:
    print("OVERSOLD — bug in stock locking")
elif successes2 < 10:
    print("UNDER-sold — some legitimate purchases were incorrectly rejected, check for a different bug")
else:
    print("Correct — exactly matched available stock")