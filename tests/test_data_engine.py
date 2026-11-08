import pytest
import pandas as pd
from sql.data_engine import DataEngine, query, get_engine

@pytest.fixture(scope="module")
def engine():
    return get_engine()

def test_engine_initialization(engine):
    assert engine is not None
    assert engine.parquet_path is not None

def test_stg_ga4_events(engine):
    df = engine.query("SELECT COUNT(*) AS cnt, COUNT(DISTINCT user_pseudo_id) AS users FROM stg_ga4__events")
    assert not df.empty
    assert df["cnt"].iloc[0] > 10000
    assert df["users"].iloc[0] > 1000

def test_stg_ga4_unnested_columns(engine):
    df = engine.query("""
        SELECT session_id, page_title, event_value, page_load_time_ms 
        FROM stg_ga4__events 
        WHERE session_id IS NOT NULL 
        LIMIT 10
    """)
    assert not df.empty
    assert "session_id" in df.columns
    assert "event_value" in df.columns
    assert "page_load_time_ms" in df.columns

def test_int_sessions_window_functions(engine):
    df = engine.query("""
        SELECT user_pseudo_id, session_id, session_sequence_number
        FROM int_sessions
        LIMIT 20
    """)
    assert not df.empty
    assert "session_sequence_number" in df.columns
    assert (df["session_sequence_number"] >= 1).all()

def test_int_funnel_stages(engine):
    df = engine.query("""
        SELECT 
            SUM(has_viewed) AS viewers,
            SUM(has_added_to_cart) AS cart_adders,
            SUM(has_checkout) AS checkout_starters,
            SUM(has_purchased) AS purchasers
        FROM int_funnel_stages
    """)
    assert not df.empty
    row = df.iloc[0]
    # In an e-commerce funnel, subsequent stages must be monotonically non-increasing
    assert row["viewers"] >= row["cart_adders"]
    assert row["cart_adders"] >= row["checkout_starters"]
    assert row["checkout_starters"] >= row["purchasers"]

def test_fct_funnel_summary(engine):
    df = engine.query("SELECT * FROM fct_funnel_summary")
    assert not df.empty
    assert "visitor_to_cart_rate" in df.columns
    assert "cart_to_checkout_rate" in df.columns
    assert "checkout_to_purchase_rate" in df.columns
    assert "overall_conversion_rate" in df.columns
    assert (df["overall_conversion_rate"] >= 0).all()
    assert (df["overall_conversion_rate"] <= 1).all()

def test_fct_cohort_retention(engine):
    df = engine.query("SELECT * FROM fct_cohort_retention")
    assert not df.empty
    assert "cohort_month" in df.columns
    assert "user_retention_rate" in df.columns
    assert "revenue_retention_rate" in df.columns
    # Month 0 user retention rate should be 1.0
    m0_df = df[df["month_number"] == 0]
    assert not m0_df.empty
    assert (m0_df["user_retention_rate"] == 1.0).all()

def test_fct_funnel_diagnostics(engine):
    df = engine.query("""
        SELECT cart_outcome, COUNT(*) AS sessions 
        FROM fct_funnel_diagnostics 
        GROUP BY cart_outcome
    """)
    assert not df.empty
    outcomes = set(df["cart_outcome"])
    assert "Abandoned" in outcomes
    assert "Completed" in outcomes
