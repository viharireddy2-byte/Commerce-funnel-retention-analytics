"""
generate_sample_data.py
Generates a realistic, high-fidelity sample Google Analytics 4 (GA4) BigQuery dataset
matching the exact schema of `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`.
Includes repeated event_params structs, device categories, traffic sources, and monthly cohorts.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone

def generate_ga4_dataset(output_path: str = "data/ga4_sample_events.parquet", num_users: int = 15000, seed: int = 42):
    np.random.seed(seed)
    random.seed(seed)

    print(f"Generating realistic GA4 eCommerce dataset with {num_users} users...")

    # Define date range: 6 monthly cohorts from Jan 2024 to Jun 2024
    start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2024, 6, 30, tzinfo=timezone.utc)
    total_days = (end_date - start_date).days

    devices = ["mobile", "desktop", "tablet"]
    device_weights = [0.60, 0.35, 0.05]

    traffic_sources = [
        ("google", "organic"),
        ("(direct)", "(none)"),
        ("google", "cpc"),
        ("facebook", "cpc"),
        ("newsletter", "email"),
        ("youtube", "referral")
    ]
    traffic_weights = [0.40, 0.25, 0.15, 0.10, 0.05, 0.05]

    user_profiles = []
    for i in range(num_users):
        u_id = f"user_{100000 + i}"
        dev = np.random.choice(devices, p=device_weights)
        ts_idx = np.random.choice(len(traffic_sources), p=traffic_weights)
        source, medium = traffic_sources[ts_idx]
        
        # User first acquisition month
        acq_day_offset = random.randint(0, total_days - 60)
        acq_date = start_date + timedelta(days=acq_day_offset)
        cohort_month = acq_date.strftime("%Y-%m")

        user_profiles.append({
            "user_pseudo_id": u_id,
            "device_category": dev,
            "traffic_source": source,
            "traffic_medium": medium,
            "acq_date": acq_date,
            "cohort_month": cohort_month
        })

    events_list = []
    session_counter = 1000000

    for user in user_profiles:
        u_id = user["user_pseudo_id"]
        dev = user["device_category"]
        source = user["traffic_source"]
        medium = user["traffic_medium"]
        first_date = user["acq_date"]

        # User activity sessions across months (Cohort decay)
        # Month 0: always active
        # Subsequent months: probability of return decays
        months_active = [0]
        decay_rates = [1.0, 0.35, 0.28, 0.23, 0.20, 0.18]
        for m in range(1, 6):
            if random.random() < decay_rates[m]:
                months_active.append(m)

        for m_offset in months_active:
            # Pick a date within that month
            session_month_date = first_date + timedelta(days=m_offset * 30 + random.randint(0, 25))
            if session_month_date > end_date:
                continue

            num_sessions = np.random.choice([1, 2, 3, 4], p=[0.70, 0.20, 0.07, 0.03])
            for s in range(num_sessions):
                session_counter += 1
                sess_id = session_counter
                session_time = session_month_date + timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )

                # Base funnel progression probability
                # Stage 1: page_view / view_item
                reached_view = True
                
                # Stage 2: add_to_cart
                # ~35% of visitors add to cart
                reached_cart = random.random() < 0.35

                # Stage 3: begin_checkout
                # MOBILE LEAK: desktop converts from cart to checkout at ~58.5%, mobile at only ~31.8%!
                if reached_cart:
                    if dev == "mobile":
                        reached_checkout = random.random() < 0.318  # Strong mobile leak!
                    elif dev == "desktop":
                        reached_checkout = random.random() < 0.585
                    else:
                        reached_checkout = random.random() < 0.420
                else:
                    reached_checkout = False

                # Stage 4: purchase
                # ~40-50% of checkouts complete purchase
                if reached_checkout:
                    reached_purchase = random.random() < (0.48 if dev == "desktop" else 0.40)
                else:
                    reached_purchase = False

                # Cart value: completed vs abandoned
                if reached_cart:
                    if reached_purchase:
                        # Normal distribution centered at $85
                        cart_value = round(float(np.random.normal(85.0, 25.0)), 2)
                        cart_value = max(15.0, cart_value)
                    else:
                        # Abandoned carts often have higher sticker shock prices
                        cart_value = round(float(np.random.exponential(120.0) + 30.0), 2)
                else:
                    cart_value = 0.0

                # Latency / load time in ms: Mobile checkout has higher latency
                base_load_time = 1200 if dev == "desktop" else (3400 if dev == "mobile" else 2200)
                page_load_time = int(np.random.normal(base_load_time, 400))
                page_load_time = max(400, page_load_time)

                current_event_time = session_time

                # 1. page_view
                date_str = current_event_time.strftime("%Y%m%d")
                ts_micros = int(current_event_time.timestamp() * 1_000_000)
                events_list.append({
                    "event_date": date_str,
                    "event_timestamp": ts_micros,
                    "event_name": "page_view",
                    "user_pseudo_id": u_id,
                    "device": {"category": dev, "operating_system": "Android" if dev == "mobile" else "Windows"},
                    "traffic_source": {"source": source, "medium": medium},
                    "geo": {"country": "United States"},
                    "event_params": [
                        {"key": "ga_session_id", "value": {"int_value": sess_id, "string_value": None, "double_value": None}},
                        {"key": "page_title", "value": {"string_value": "Home & Catalog", "int_value": None, "double_value": None}},
                        {"key": "page_load_time_ms", "value": {"int_value": page_load_time, "string_value": None, "double_value": None}}
                    ]
                })

                # 2. view_item
                current_event_time += timedelta(seconds=random.randint(15, 60))
                ts_micros = int(current_event_time.timestamp() * 1_000_000)
                events_list.append({
                    "event_date": date_str,
                    "event_timestamp": ts_micros,
                    "event_name": "view_item",
                    "user_pseudo_id": u_id,
                    "device": {"category": dev, "operating_system": "Android" if dev == "mobile" else "Windows"},
                    "traffic_source": {"source": source, "medium": medium},
                    "geo": {"country": "United States"},
                    "event_params": [
                        {"key": "ga_session_id", "value": {"int_value": sess_id, "string_value": None, "double_value": None}},
                        {"key": "page_title", "value": {"string_value": "Product Detail Page", "int_value": None, "double_value": None}},
                        {"key": "page_load_time_ms", "value": {"int_value": page_load_time + random.randint(-100, 200), "string_value": None, "double_value": None}}
                    ]
                })

                # 3. add_to_cart
                if reached_cart:
                    current_event_time += timedelta(seconds=random.randint(30, 120))
                    ts_micros = int(current_event_time.timestamp() * 1_000_000)
                    events_list.append({
                        "event_date": date_str,
                        "event_timestamp": ts_micros,
                        "event_name": "add_to_cart",
                        "user_pseudo_id": u_id,
                        "device": {"category": dev, "operating_system": "Android" if dev == "mobile" else "Windows"},
                        "traffic_source": {"source": source, "medium": medium},
                        "geo": {"country": "United States"},
                        "event_params": [
                            {"key": "ga_session_id", "value": {"int_value": sess_id, "string_value": None, "double_value": None}},
                            {"key": "page_title", "value": {"string_value": "Cart", "int_value": None, "double_value": None}},
                            {"key": "value", "value": {"double_value": cart_value, "int_value": None, "string_value": None}},
                            {"key": "page_load_time_ms", "value": {"int_value": page_load_time + random.randint(100, 300), "string_value": None, "double_value": None}}
                        ]
                    })

                # 4. begin_checkout
                if reached_checkout:
                    current_event_time += timedelta(seconds=random.randint(20, 90))
                    ts_micros = int(current_event_time.timestamp() * 1_000_000)
                    checkout_latency = page_load_time + (1400 if dev == "mobile" else 200)
                    events_list.append({
                        "event_date": date_str,
                        "event_timestamp": ts_micros,
                        "event_name": "begin_checkout",
                        "user_pseudo_id": u_id,
                        "device": {"category": dev, "operating_system": "Android" if dev == "mobile" else "Windows"},
                        "traffic_source": {"source": source, "medium": medium},
                        "geo": {"country": "United States"},
                        "event_params": [
                            {"key": "ga_session_id", "value": {"int_value": sess_id, "string_value": None, "double_value": None}},
                            {"key": "page_title", "value": {"string_value": "Checkout Step 1", "int_value": None, "double_value": None}},
                            {"key": "value", "value": {"double_value": cart_value, "int_value": None, "string_value": None}},
                            {"key": "page_load_time_ms", "value": {"int_value": checkout_latency, "string_value": None, "double_value": None}}
                        ]
                    })

                # 5. purchase
                if reached_purchase:
                    current_event_time += timedelta(seconds=random.randint(45, 180))
                    ts_micros = int(current_event_time.timestamp() * 1_000_000)
                    events_list.append({
                        "event_date": date_str,
                        "event_timestamp": ts_micros,
                        "event_name": "purchase",
                        "user_pseudo_id": u_id,
                        "device": {"category": dev, "operating_system": "Android" if dev == "mobile" else "Windows"},
                        "traffic_source": {"source": source, "medium": medium},
                        "geo": {"country": "United States"},
                        "event_params": [
                            {"key": "ga_session_id", "value": {"int_value": sess_id, "string_value": None, "double_value": None}},
                            {"key": "page_title", "value": {"string_value": "Order Confirmation", "int_value": None, "double_value": None}},
                            {"key": "value", "value": {"double_value": cart_value, "int_value": None, "string_value": None}},
                            {"key": "page_load_time_ms", "value": {"int_value": page_load_time, "string_value": None, "double_value": None}}
                        ]
                    })

    df = pd.DataFrame(events_list)
    print(f"Total events generated: {len(df):,} across {num_users:,} users.")
    
    # Save to parquet
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_parquet(output_path, index=False, engine="pyarrow")
    print(f"Saved dataset to {output_path} ({os.path.getsize(output_path) / 1024 / 1024:.2f} MB)")
    return output_path

if __name__ == "__main__":
    generate_ga4_dataset()
