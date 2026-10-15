"""Generate small, reproducible sample CSVs into ./seeds (run once from project root)."""
import csv, random
from datetime import date, datetime, timedelta

random.seed(42)
countries = ["IN", "US", "UK", "DE", "AE", "SG"]
channels = ["web", "mobile", "marketplace"]
categories = ["Electronics", "Home", "Fashion", "Sports", "Books"]

with open("seeds/raw_customers.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["customer_id", "full_name", "email", "country", "signup_date"])
    for i in range(1, 501):
        d = date(2026, 1, 1) + timedelta(days=random.randint(0, 270))
        w.writerow([i, f"  Customer {i} ", f"User{i}@Example.com ", random.choice(countries), d])

products = []
with open("seeds/raw_products.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["product_id", "product_name", "category", "unit_price"])
    for i in range(1, 41):
        price = round(random.uniform(5, 300), 2); products.append((i, price))
        w.writerow([i, f"Product {i}", random.choice(categories), price])

orders, items = [], []
for oid in range(1, 3001):
    ts = datetime(2026, 4, 1) + timedelta(days=random.randint(0, 182), seconds=random.randint(0, 86399))
    status = random.choices(["completed", "cancelled", "returned"], [0.82, 0.10, 0.08])[0]
    orders.append([oid, random.randint(1, 500), ts.isoformat(sep=" "), status, random.choice(channels)])
    for pid, price in random.sample(products, random.randint(1, 4)):   # distinct products per order
        items.append([oid, pid, random.randint(1, 3), price])

with open("seeds/raw_orders.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["order_id", "customer_id", "order_ts", "status", "channel"]); w.writerows(orders)
with open("seeds/raw_order_items.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["order_id", "product_id", "quantity", "unit_price"]); w.writerows(items)
print("seeds written")
