import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

import asyncpg
from faker import Faker

fake = Faker()

CATEGORIES = ["Apparel", "Shoes", "Beauty", "Electronics", "Home", "Fitness", "Outdoors"]
CARRIERS = ["UPS", "USPS", "FedEx", "DHL"]
UTM_SOURCES = ["google", "meta", "tiktok", "newsletter", "affiliate"]
CAMPAIGNS = ["brand", "promo", "retargeting", "new_arrivals", "clearance"]


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def seed_all(conn: asyncpg.Connection) -> None:
    random.seed(7)
    Faker.seed(7)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=365)

    # Products
    products = []
    for i in range(250):
        category = random.choice(CATEGORIES)
        sku = f"SKU-{i:05d}"
        name = f"{fake.color_name()} {category[:-1] if category.endswith('s') else category} {fake.word().title()}"
        unit_price = round(random.uniform(8, 250), 2)
        products.append((sku, name, category, unit_price, True))

    await conn.executemany(
        "insert into products(sku,name,category,unit_price,active) values($1,$2,$3,$4,$5)",
        products,
    )

    product_rows = await conn.fetch("select product_id, category, unit_price from products")
    product_ids = [r["product_id"] for r in product_rows]
    price_by_product = {r["product_id"]: float(r["unit_price"]) for r in product_rows}

    # Customers
    countries = ["US", "CA", "GB", "DE", "FR", "AU"]
    customers = []
    for _ in range(3500):
        created_at = _utc(fake.date_time_between(start_date=start, end_date=now))
        email = fake.unique.email()
        customers.append(
            (
                created_at,
                email,
                fake.first_name(),
                fake.last_name(),
                random.choice(countries),
                random.random() < 0.55,
            )
        )

    await conn.executemany(
        "insert into customers(created_at,email,first_name,last_name,country,marketing_opt_in) values($1,$2,$3,$4,$5,$6)",
        customers,
    )
    customer_ids = [r["customer_id"] for r in await conn.fetch("select customer_id from customers")]

    # Orders + items + payments + shipments + refunds
    order_rows = []
    order_items_rows = []
    payment_rows = []
    shipment_rows = []
    refund_rows = []

    order_count = 22000
    for _ in range(order_count):
        cust = random.choice(customer_ids)
        order_ts = _utc(fake.date_time_between(start_date=start, end_date=now))
        channel = random.choices(["web", "mobile", "marketplace"], weights=[0.55, 0.30, 0.15])[0]

        # build cart
        item_n = random.choices([1, 2, 3, 4], weights=[0.55, 0.25, 0.14, 0.06])[0]
        items = random.sample(product_ids, k=item_n)
        subtotal = 0.0
        for pid in items:
            qty = random.choices([1, 2, 3], weights=[0.78, 0.18, 0.04])[0]
            unit = price_by_product[pid]
            discount = round(unit * qty * (0.0 if random.random() < 0.72 else random.uniform(0.05, 0.25)), 2)
            subtotal += unit * qty - discount
            order_items_rows.append((pid, qty, unit, discount))  # order_id filled later

        shipping_cost = round(random.choices([0, 4.99, 7.99, 11.99], weights=[0.22, 0.44, 0.26, 0.08])[0], 2)
        total = round(subtotal + shipping_cost, 2)

        # status flow
        paid = random.random() < 0.93
        cancelled = (not paid) and (random.random() < 0.65)
        refunded = paid and (random.random() < 0.08)

        status = "placed"
        if cancelled:
            status = "cancelled"
        elif paid:
            status = "paid"

        order_rows.append((cust, order_ts, status, channel, "USD", shipping_cost, total))

    # Insert orders and keep totals in a temp table via CTE
    await conn.execute("create temp table tmp_orders(cust bigint, order_ts timestamptz, status text, channel text, currency text, shipping_cost numeric, total numeric) on commit drop")
    await conn.copy_records_to_table("tmp_orders", records=order_rows)
    inserted = await conn.fetch(
        """
        insert into orders(customer_id, order_ts, status, channel, currency, shipping_cost)
        select cust, order_ts, status, channel, currency, shipping_cost from tmp_orders
        returning order_id, order_ts, status
        """
    )
    order_ids = [r["order_id"] for r in inserted]

    # attach items to orders
    idx = 0
    items_with_order = []
    for oid in order_ids:
        # regenerate item count deterministically from oid
        random.seed(oid)
        item_n = random.choices([1, 2, 3, 4], weights=[0.55, 0.25, 0.14, 0.06])[0]
        chunk = order_items_rows[idx : idx + item_n]
        idx += item_n
        for (pid, qty, unit, discount) in chunk:
            items_with_order.append((oid, pid, qty, unit, discount))

    await conn.executemany(
        "insert into order_items(order_id, product_id, quantity, unit_price, discount) values($1,$2,$3,$4,$5)",
        items_with_order,
    )

    # compute order totals from items
    await conn.execute(
        """
        create temp table tmp_totals as
        select o.order_id,
               round(sum(oi.quantity*oi.unit_price - oi.discount)::numeric, 2) as items_total
        from orders o join order_items oi on oi.order_id=o.order_id
        group by 1;
        """
    )

    # payments + shipments + some refunds
    order_meta = await conn.fetch(
        """
        select o.order_id, o.order_ts, o.status, o.shipping_cost,
               t.items_total,
               (t.items_total + o.shipping_cost)::numeric(12,2) as order_total
        from orders o join tmp_totals t using(order_id)
        """
    )

    for r in order_meta:
        oid = r["order_id"]
        order_ts = r["order_ts"]
        status = r["status"]
        order_total = float(r["order_total"])

        if status == "cancelled":
            continue

        paid_ts = order_ts + timedelta(minutes=random.randint(1, 60*6))
        method = random.choices(["card", "paypal", "apple_pay", "klarna"], weights=[0.72, 0.14, 0.10, 0.04])[0]

        # shipments
        shipped_ts = paid_ts + timedelta(hours=random.randint(2, 72))
        service_level = random.choices(["standard", "expedited", "overnight"], weights=[0.76, 0.20, 0.04])[0]
        carrier = random.choice(CARRIERS)
        transit_days = {"standard": random.randint(3, 7), "expedited": random.randint(2, 4), "overnight": 1}[service_level]
        delivered_ts = shipped_ts + timedelta(days=transit_days, hours=random.randint(0, 12))

        # some lost/returned
        shipment_status = "delivered"
        if random.random() < 0.007:
            shipment_status = "lost"
            delivered_ts = None
        elif random.random() < 0.03:
            shipment_status = "returned"

        shipment_rows.append((oid, carrier, service_level, shipped_ts, delivered_ts, shipment_status))

        # refunds
        is_refunded = random.random() < 0.08
        if is_refunded:
            refund_amt = round(order_total * random.uniform(0.25, 1.0), 2)
            refund_ts = delivered_ts + timedelta(days=random.randint(1, 21)) if delivered_ts else shipped_ts + timedelta(days=random.randint(7, 30))
            reason = random.choices(["damaged", "late_delivery", "wrong_item", "changed_mind", "other"], weights=[0.18, 0.18, 0.22, 0.34, 0.08])[0]
            refund_rows.append((oid, refund_ts, refund_amt, reason))
            pay_status = "partial_refund" if refund_amt < order_total else "refunded"
        else:
            pay_status = "paid"

        payment_rows.append((oid, paid_ts, method, round(order_total, 2), pay_status))

    await conn.executemany(
        "insert into payments(order_id, paid_ts, method, amount, status) values($1,$2,$3,$4,$5)",
        payment_rows,
    )
    await conn.executemany(
        "insert into shipments(order_id, carrier, service_level, shipped_ts, delivered_ts, status) values($1,$2,$3,$4,$5,$6)",
        shipment_rows,
    )
    await conn.executemany(
        "insert into refunds(order_id, refund_ts, amount, reason) values($1,$2,$3,$4)",
        refund_rows,
    )

    # Update order statuses based on payment/shipment/refund
    await conn.execute(
        """
        update orders o
        set status = case
          when p.status in ('refunded','partial_refund') then 'refunded'
          when s.status = 'delivered' then 'delivered'
          when s.status = 'shipped' then 'shipped'
          else o.status
        end
        from payments p
        left join shipments s on s.order_id=o.order_id
        where p.order_id=o.order_id;
        """
    )

    # Web events (funnel-ish)
    # Sample about 5x order count sessions
    events = []
    session_count = 90000
    for _ in range(session_count):
        event_ts = _utc(fake.date_time_between(start_date=start, end_date=now))
        session_id = uuid.uuid4()
        channel = random.choices(["web", "mobile"], weights=[0.62, 0.38])[0]
        utm_source = random.choice(UTM_SOURCES)
        utm_campaign = random.choice(CAMPAIGNS)

        known_customer = random.random() < 0.35
        customer_id = random.choice(customer_ids) if known_customer else None

        # Start
        events.append((event_ts, session_id, customer_id, "session_start", None, channel, utm_source, utm_campaign))

        # Views
        view_n = random.choices([1, 2, 3, 4, 5], weights=[0.18, 0.26, 0.24, 0.18, 0.14])[0]
        last_ts = event_ts
        last_product = None
        for _i in range(view_n):
            last_ts = last_ts + timedelta(seconds=random.randint(10, 240))
            last_product = random.choice(product_ids)
            events.append((last_ts, session_id, customer_id, "product_view", last_product, channel, utm_source, utm_campaign))

        # Add to cart
        if random.random() < 0.32:
            last_ts = last_ts + timedelta(seconds=random.randint(5, 120))
            events.append((last_ts, session_id, customer_id, "add_to_cart", last_product, channel, utm_source, utm_campaign))

            # Checkout
            if random.random() < 0.55:
                last_ts = last_ts + timedelta(seconds=random.randint(20, 180))
                events.append((last_ts, session_id, customer_id, "checkout_start", last_product, channel, utm_source, utm_campaign))

                # Purchase event (not 1:1 with orders; enough for funnel)
                if random.random() < 0.72:
                    last_ts = last_ts + timedelta(seconds=random.randint(30, 300))
                    events.append((last_ts, session_id, customer_id, "purchase", last_product, channel, utm_source, utm_campaign))

    await conn.executemany(
        """
        insert into web_events(event_ts, session_id, customer_id, event_type, product_id, channel, utm_source, utm_campaign)
        values($1,$2,$3,$4,$5,$6,$7,$8)
        """,
        events,
    )
