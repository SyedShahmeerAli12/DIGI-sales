"""
Generates a synthetic-but-realistic FMCG Pakistan sales dataset into
backend/data/fmcg_sales.db (SQLite). Parameters grounded in real research
(real brand names/categories, real Pakistani cities, real Ramadan/Eid 2026
dates) — but the actual transactions/customers/invoices are necessarily
synthetic, since no such data is publicly available. See conversation
history for the research behind the scale (~200 SKUs matches real Pakistani
FMCG companies like Unilever Pakistan / National Foods).

Run from backend/: python -m app.scripts.generate_fmcg_data
"""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "fmcg_sales.db"

rng = np.random.default_rng(42)

# --- Real-world grounded constants -----------------------------------------

END_DATE = date(2026, 7, 28)
START_DATE = END_DATE - timedelta(days=364)

RAMADAN_START, RAMADAN_END = date(2026, 2, 19), date(2026, 3, 20)
EID_UL_FITR = date(2026, 3, 21)
EID_UL_ADHA = date(2026, 5, 27)

REGIONS = ["North", "South", "Central", "West"]
CITIES_BY_REGION = {
    "North": ["Islamabad", "Rawalpindi"],
    "South": ["Karachi", "Hyderabad"],
    "Central": ["Lahore", "Faisalabad", "Gujranwala", "Sialkot"],
    "West": ["Peshawar", "Quetta"],
}
CHANNELS = ["Retail", "Wholesale", "Modern Trade", "Pharmacy"]
CHANNEL_WEIGHTS = [0.65, 0.15, 0.12, 0.08]

CATEGORY_BRANDS = {
    "Tea": (["Lipton", "Tapal", "Brooke Bond Supreme", "Vital"], ["95g", "190g", "475g", "950g"]),
    "Soap": (["Lifebuoy", "Lux", "Dove", "Safeguard"], ["100g", "135g", "175g", "250g"]),
    "Detergent": (["Surf Excel", "Ariel", "Bonus"], ["150g", "500g", "1kg", "2.5kg"]),
    "Biscuits": (["Peek Freans", "LU Prince", "Sooper", "Rio"], ["small pack", "family pack", "jumbo pack"]),
    "Spices": (["National", "Shan"], ["50g", "100g", "200g", "400g"]),
    "Beverages": (["Pepsi", "Coca-Cola", "Sprite", "7Up"], ["250ml", "500ml", "1L", "1.5L"]),
    "Dairy": (["Olpers", "Nestle Milkpak", "Nurpur"], ["250ml", "500ml", "1L"]),
    "Snacks": (["Lays", "Kurkure", "Cheetos"], ["small pack", "family pack"]),
    "Personal Care": (["Vaseline", "Fair & Lovely", "Nivea"], ["100ml", "200ml", "300ml"]),
    "Oral Care": (["Closeup", "Colgate", "Sensodyne"], ["70g", "140g", "190g"]),
    "Hair Care": (["Sunsilk", "Head & Shoulders", "Pantene"], ["180ml", "360ml", "700ml"]),
}

FIRST_NAMES = [
    "Ahmed", "Ali", "Bilal", "Usman", "Hamza", "Kashif", "Faisal", "Zainab",
    "Ayesha", "Sana", "Rashid", "Imran", "Tariq", "Waqas", "Adeel", "Saad",
    "Hassan", "Hussain", "Naveed", "Shahzad", "Asim", "Zeeshan", "Junaid",
    "Amir", "Farhan", "Sohail", "Nadia", "Farah", "Mehwish", "Rabia",
]
LAST_NAMES = [
    "Khan", "Raza", "Sheikh", "Tariq", "Malik", "Iqbal", "Rauf", "Hussain",
    "Mehmood", "Farooq", "Butt", "Chaudhry", "Ahmed", "Aziz", "Baig",
]

CUSTOMER_SUFFIXES = [
    "Store", "General Store", "Super Market", "Cash & Carry", "Traders",
    "Mart", "Provision Store", "Enterprises",
]

RETURN_REASONS = ["Damaged", "Expired", "Wrong item delivered", "Excess stock"]


def season_for(d: date) -> str:
    if d.month in (12, 1, 2):
        return "Winter"
    if d.month in (6, 7, 8):
        return "Summer"
    return "Moderate"


def build_dim_date() -> pd.DataFrame:
    days = pd.date_range(START_DATE, END_DATE, freq="D")
    df = pd.DataFrame({"date": days.strftime("%Y-%m-%d")})
    df["day"] = days.day
    df["week"] = days.isocalendar().week.values
    df["month"] = days.month
    df["month_name"] = days.strftime("%B")
    df["quarter"] = days.quarter
    df["year"] = days.year
    df["weekday_name"] = days.strftime("%A")
    df["is_weekend"] = days.weekday.isin([4, 5]).astype(int)  # Fri/Sat weekend in Pakistan
    df["is_ramadan"] = [(RAMADAN_START <= d.date() <= RAMADAN_END) for d in days]
    df["is_ramadan"] = df["is_ramadan"].astype(int)
    df["is_eid"] = [
        (d.date() in (EID_UL_FITR, EID_UL_FITR + timedelta(days=1), EID_UL_FITR + timedelta(days=2))
         or d.date() in (EID_UL_ADHA, EID_UL_ADHA + timedelta(days=1), EID_UL_ADHA + timedelta(days=2)))
        for d in days
    ]
    df["is_eid"] = df["is_eid"].astype(int)
    df["season"] = [season_for(d.date()) for d in days]
    return df


def build_dim_sales_org():
    regions = pd.DataFrame({"region_id": range(1, len(REGIONS) + 1), "region_name": REGIONS})

    managers = []
    mid = 1
    for region_id in range(1, len(REGIONS) + 1):
        for _ in range(2):
            managers.append({
                "manager_id": mid,
                "manager_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "region_id": region_id,
            })
            mid += 1
    managers = pd.DataFrame(managers)

    territories = []
    tid = 1
    for _, m in managers.iterrows():
        for _ in range(3):
            territories.append({
                "territory_id": tid,
                "territory_name": f"{REGIONS[m['region_id'] - 1]} Territory {tid}",
                "manager_id": m["manager_id"],
            })
            tid += 1
    territories = pd.DataFrame(territories)

    areas = []
    aid = 1
    for _, t in territories.iterrows():
        region_name = REGIONS[managers.loc[managers["manager_id"] == t["manager_id"], "region_id"].iloc[0] - 1]
        city = rng.choice(CITIES_BY_REGION[region_name])
        for _ in range(5):
            areas.append({
                "area_id": aid,
                "area_name": f"{city} Area {aid}",
                "city": city,
                "territory_id": t["territory_id"],
            })
            aid += 1
    areas = pd.DataFrame(areas)

    bookers = []
    bid = 1
    for _, a in areas.iterrows():
        supervisor = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        for _ in range(rng.integers(1, 2, endpoint=True) + 0):
            bookers.append({
                "booker_id": bid,
                "booker_name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                "supervisor_name": supervisor,
                "area_id": a["area_id"],
            })
            bid += 1
    bookers = pd.DataFrame(bookers)

    return regions, managers, territories, areas, bookers


def build_dim_product():
    rows = []
    pid = 1
    for category, (brands, packs) in CATEGORY_BRANDS.items():
        for brand in brands:
            for pack in packs:
                base_cost = rng.uniform(50, 900)
                rows.append({
                    "product_id": pid,
                    "product_name": f"{brand} {pack}",
                    "brand": brand,
                    "category": category,
                    "pack_size": pack,
                    "cost": round(base_cost, 2),
                    "price": round(base_cost * rng.uniform(1.15, 1.45), 2),
                })
                pid += 1
    df = pd.DataFrame(rows)
    return df.sample(n=min(200, len(df)), random_state=42).reset_index(drop=True).assign(
        product_id=lambda d: range(1, len(d) + 1)
    )


def build_dim_customer(areas: pd.DataFrame, n=5000):
    rows = []
    for i in range(1, n + 1):
        area = areas.sample(1, random_state=None).iloc[0]
        rows.append({
            "customer_id": i,
            "customer_name": f"{rng.choice(LAST_NAMES)} {rng.choice(CUSTOMER_SUFFIXES)}",
            "channel": rng.choice(CHANNELS, p=CHANNEL_WEIGHTS),
            "area_id": int(area["area_id"]),
            "city": area["city"],
            "credit_limit": int(rng.choice([0, 50000, 100000, 200000])),
        })
    return pd.DataFrame(rows)


def seasonal_multiplier(category: str, is_ramadan: bool, is_eid: bool, season: str) -> float:
    m = 1.0
    if is_ramadan and category in ("Tea", "Spices", "Dairy", "Beverages"):
        m *= 1.6
    if is_eid and category in ("Detergent", "Personal Care", "Oral Care", "Hair Care"):
        m *= 1.8
    if season == "Summer" and category == "Beverages":
        m *= 1.5
    if season == "Winter" and category == "Tea":
        m *= 1.3
    return m


def build_facts(dim_date, products, customers, bookers):
    invoices = []
    lines = []
    invoice_id = 1
    line_id = 1

    booker_ids = bookers["booker_id"].to_numpy()
    customer_rows = customers.to_dict("records")
    product_rows = products.to_dict("records")

    for _, drow in dim_date.iterrows():
        d = drow["date"]
        base_invoices_today = rng.integers(140, 200)
        mult = 1.0
        if drow["is_ramadan"]:
            mult *= 1.3
        if drow["is_eid"]:
            mult *= 1.6
        if drow["is_weekend"]:
            mult *= 0.8
        n_invoices_today = int(base_invoices_today * mult)

        day_customers = rng.choice(len(customer_rows), size=n_invoices_today, replace=True)
        day_bookers = rng.choice(booker_ids, size=n_invoices_today, replace=True)

        for ci, bk in zip(day_customers, day_bookers):
            cust = customer_rows[ci]
            invoices.append({
                "invoice_id": invoice_id,
                "date": d,
                "customer_id": cust["customer_id"],
                "booker_id": int(bk),
            })

            n_lines = rng.integers(3, 13) if cust["channel"] != "Modern Trade" else rng.integers(2, 6)
            chosen_products = rng.choice(len(product_rows), size=n_lines, replace=False)
            for pi in chosen_products:
                prod = product_rows[pi]
                mult_qty = seasonal_multiplier(prod["category"], bool(drow["is_ramadan"]), bool(drow["is_eid"]), drow["season"])
                base_qty = rng.integers(1, 20) if cust["channel"] in ("Wholesale", "Modern Trade") else rng.integers(1, 8)
                qty = max(1, int(base_qty * mult_qty))
                discount_pct = rng.choice([0, 0, 0, 5, 8, 10])
                gross = qty * prod["price"]
                net = round(gross * (1 - discount_pct / 100), 2)
                lines.append({
                    "line_id": line_id,
                    "invoice_id": invoice_id,
                    "product_id": prod["product_id"],
                    "qty": qty,
                    "unit_price": prod["price"],
                    "discount_pct": discount_pct,
                    "net_sale": net,
                })
                line_id += 1
            invoice_id += 1

    return pd.DataFrame(invoices), pd.DataFrame(lines)


def build_returns(invoice_lines: pd.DataFrame, invoices: pd.DataFrame):
    sample = invoice_lines.sample(frac=0.02, random_state=42)
    inv_dates = invoices.set_index("invoice_id")["date"]
    rows = []
    for i, (_, r) in enumerate(sample.iterrows(), start=1):
        rows.append({
            "return_id": i,
            "date": inv_dates.loc[r["invoice_id"]],
            "invoice_id": r["invoice_id"],
            "product_id": r["product_id"],
            "qty": max(1, int(r["qty"] * rng.uniform(0.1, 0.5))),
            "reason": rng.choice(RETURN_REASONS),
        })
    return pd.DataFrame(rows)


def build_inventory(dim_date, products):
    rows = []
    stock = {p: int(rng.integers(500, 2000)) for p in products["product_id"]}
    for _, drow in dim_date.iterrows():
        for _, prod in products.iterrows():
            pid = prod["product_id"]
            received = int(rng.integers(0, 300)) if rng.random() < 0.3 else 0
            issued = int(rng.integers(0, 250))
            opening = stock[pid]
            closing = max(0, opening + received - issued)
            stock[pid] = closing
            rows.append({
                "date": drow["date"], "product_id": pid,
                "opening_stock": opening, "received": received,
                "issued": issued, "closing_stock": closing,
            })
    return pd.DataFrame(rows)


def build_targets(bookers, dim_date):
    months = dim_date["date"].str.slice(0, 7).unique()
    rows = []
    tid = 1
    for month in months:
        for _, b in bookers.iterrows():
            target_value = int(rng.integers(80000, 200000))
            achievement_ratio = rng.normal(0.92, 0.15)
            achieved_value = max(0, int(target_value * achievement_ratio))
            rows.append({
                "target_id": tid, "month": month, "booker_id": b["booker_id"],
                "target_value": target_value, "achieved_value": achieved_value,
            })
            tid += 1
    return pd.DataFrame(rows)


def main():
    print("Building dimensions...")
    dim_date = build_dim_date()
    regions, managers, territories, areas, bookers = build_dim_sales_org()
    products = build_dim_product()
    customers = build_dim_customer(areas, n=5000)

    print(f"  dim_date={len(dim_date)} regions={len(regions)} managers={len(managers)} "
          f"territories={len(territories)} areas={len(areas)} bookers={len(bookers)} "
          f"products={len(products)} customers={len(customers)}")

    print("Building facts (this generates invoices day-by-day, may take a minute)...")
    invoices, invoice_lines = build_facts(dim_date, products, customers, bookers)
    print(f"  invoices={len(invoices)} invoice_lines={len(invoice_lines)}")

    returns = build_returns(invoice_lines, invoices)
    inventory = build_inventory(dim_date, products)
    targets = build_targets(bookers, dim_date)
    print(f"  returns={len(returns)} inventory={len(inventory)} targets={len(targets)}")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)

    dim_date.to_sql("dim_date", conn, index=False)
    regions.to_sql("dim_region", conn, index=False)
    managers.to_sql("dim_sales_manager", conn, index=False)
    territories.to_sql("dim_territory", conn, index=False)
    areas.to_sql("dim_area", conn, index=False)
    bookers.to_sql("dim_order_booker", conn, index=False)
    products.to_sql("dim_product", conn, index=False)
    customers.to_sql("dim_customer", conn, index=False)
    invoices.to_sql("fact_invoice_header", conn, index=False)
    invoice_lines.to_sql("fact_invoice_line", conn, index=False)
    returns.to_sql("fact_returns", conn, index=False)
    inventory.to_sql("fact_inventory", conn, index=False)
    targets.to_sql("fact_targets", conn, index=False)

    conn.commit()
    conn.close()
    print(f"Wrote database to {DB_PATH}")


if __name__ == "__main__":
    main()
