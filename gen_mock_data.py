"""
generate_mock_data.py
---------------------
Generates 12 months of realistic mock KPI data for a mortgage origination portal
and loads it into a PostgreSQL database (tables must already exist).
 
USAGE:
  python generate_mock_data.py
 
CONFIGURATION:
  Edit the DB_CONFIG block below to match your local Postgres credentials.
 
LOAD ORDER (respects FK constraints):
  1. sprint_metrics        (parent — no dependencies)
  2. product_events        (no dependencies)
  3. daily_engagement      (FK → sprint_metrics.sprint_id)
  4. daily_conversion      (FK → sprint_metrics.sprint_id)
  5. daily_satisfaction    (no FK)
"""

import os 
import random
from datetime import date, timedelta
 
import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

#----------------------------------------------------------------------
# DB Config - loaded from .env file for security
#----------------------------------------------------------------------
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'dbname': os.getenv('DB_NAME', 'mortgage_portal_kpi'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

# ----------------------------------------------------------------------
# Date Range (12 months of daily snapshots)
# ----------------------------------------------------------------------
START_DATE = date(2024, 6, 1)
END_DATE = date(2025, 5, 31)

random.seed(42)
np.random.seed(42)

# ----------------------------------------------------------------------
# Helper Utilities
# ----------------------------------------------------------------------

def daterange(start: date, end: date):
    """Yield every date from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def seasonality(d: date) -> float:
    """
    Mortgage origination sesonality multiplier.
    Spring surge (Mar-Jun) ~1.3x, summer peak (July - Aug) ~1.2x,
    winter slow (Dec - Feb) ~0.7x.
    """

    curve = {
        1: 0.70, 2: 0.75, 3: 1.10, 4: 1.25,
        5: 1.30, 6: 1.20, 7: 1.15, 8: 1.10,
        9: 1.00, 10: 0.90, 11: 0.80, 12: 0.72,
    }
    return curve[d.month]

def is_weekday(d: date) -> bool:
    """Returns True if the date is a weekday (Mon-Fri)."""
    return d.weekday() < 5

def noise(scale: float = 1.0) -> float:
    """Returns a random noise value from a normal distribution."""
    return np.random.normal(0, scale)

def sprint_id_for_date(d: date, sprint_map: dict) -> int:
    """ Returns the sprint_id for a given date based on the sprint mapping."""
    for sid, (s_start, s_end) in sprint_map.items():
        if s_start <= d <= s_end:
            return sid
    #Fallback: last sprint id
    return max(sprint_map.keys())

# ----------------------------------------------------------------------
# Product Events
# ----------------------------------------------------------------------

PRODUCT_EVENTS = [
    {
        "date": date(2024, 9, 10),
        "event_type": "release",
        "description": "v2.1 launch: streamlined income verification step, new progress bar UX. "
                       "Expected lift in conversion and drop in doc-stage abandonment.",  
    },
    {
        "date": date(2025, 2, 18),
        "event_type": "release",
        "description": "v2.5 launch: pre-qual calculator redesign and mobile-responsive document upload. "
                       "Expected lift in feature adoption and DAU on mobile.",
    },
    {
        "date": date(2024, 11, 14),
        "event_type": "incident",
        "description":  "P1 outage — document upload service down for ~6 hours. "
                       "Support ticket spike expected. NPS impact ~-8 pts over 2 weeks.",
    },
    {
        "date": date(2025, 3, 5),
        "event_type": "rate_change",
        "description": "30-year fixed rate crosses 7.5%. Application volume expected to soften 10-15% "
                       "over following 6 weeks as buyer affordability tightens.",
    },
    {
        "date": date(2024, 8, 1),
        "event_type": "campaign",
        "description": "Summer first-time homebuyer digital campaign launch. "
                       "Targeted paid social driving incremental session volume through August.",
    },
]

# Srint themes - maps sprint_id to a plain_english focus description
SPRINT_THEMES = {
    1:  "Onboarding flow audit and quick wins",
    2:  "Identity verification step refactor",
    3:  "Income documentation UI improvements",
    4:  "Performance optimisation and bug backlog",
    5:  "Pre-qual calculator v1 build",
    6:  "Rate estimator widget integration",
    7:  "v2.1 release prep — income step simplification",
    8:  "v2.1 stabilisation and regression fixes",
    9:  "Document upload service reliability hardening",
    10: "Progress bar UX and applicant status page",
    11: "P1 incident post-mortem and remediation",
    12: "Incident follow-up: upload service rebuild",
    13: "Accessibility audit and WCAG compliance",
    14: "Mobile responsiveness — phase 1",
    15: "Mobile responsiveness — phase 2 (doc upload)",
    16: "Pre-qual calculator redesign — v2.5 prep",
    17: "v2.5 release prep and QA",
    18: "v2.5 stabilisation and A/B test setup",
    19: "Conversion funnel analytics instrumentation",
    20: "Rate environment response — affordability tools",
    21: "Co-borrower flow enhancements",
    22: "Notification and status email improvements",
    23: "Backlog grooming and tech debt sprint",
    24: "Dashboard and reporting features (internal)",
    25: "Compliance review — TRID disclosure updates",
    26: "Roadmap planning and discovery sprint",
    27: "Capacity buffer — stretch goals only",
}


# Drop-off reasons by stage - realistic causal vocabulary
DROP_OFF_REASONS = {
    "identity":  ["ssn_validation_failed", "id_document_mismatch", "user_abandoned", "session_timeout"],
    "income":    ["document_format_unsupported", "income_threshold_not_met", "user_abandoned", "returned_later"],
    "docs":      ["upload_error", "file_size_exceeded", "user_abandoned", "session_timeout"],
    "review":    ["user_abandoned", "returned_later", "application_expired", "rate_lock_expired"],
}

# Reason weights shift on incident day (upload_error dominates at docs stage)
DROP_OFF_REASON_WEIGHTS_NORMAL = {
    "identity":  [0.20, 0.15, 0.45, 0.20],
    "income":    [0.20, 0.15, 0.45, 0.20],
    "docs":      [0.15, 0.10, 0.50, 0.25],
    "review":    [0.45, 0.25, 0.20, 0.10],
}
 
DROP_OFF_REASON_WEIGHTS_INCIDENT = {
    "identity":  [0.20, 0.15, 0.45, 0.20],
    "income":    [0.20, 0.15, 0.45, 0.20],
    "docs":      [0.75, 0.10, 0.10, 0.05],   # upload_error dominates
    "review":    [0.45, 0.25, 0.20, 0.10],
}

#----------------------------------------------------------------------
# Table Generators
#----------------------------------------------------------------------
def generate_sprint_metrics() -> pd.DataFrame:
    """Generate first - daily tables need the sprint_map lookup."""
    rows = []
    sprint_start = START_DATE
    sprint_id = 1

    while sprint_start <= END_DATE:
        sprint_end = sprint_start + timedelta(days=13)

        #Velocity: rmp early, plateu mid-year, slight did at incident sprint
        if sprint_id <= 4:
            base_velocity = 28 + sprint_id * 3
        elif sprint_id == 12:
            base_velocity = 38
        elif sprint_id <= 18:
            base_velocity = 52
        else:
            base_velocity = 50

        planned = max(20, int(base_velocity + noise(4)))
        completed = max(10, int(planned * random.uniform(0.78, 0.97))) 

        #Bug volume spokes around incident and rate change sprints
        base_bugs = 6
        if sprint_start <= date(2024, 11, 14) <= sprint_end:
            base_bugs = 22
        elif sprint_start <= date(2025, 3, 5) <= sprint_end:
            base_bugs = 10
        bugs_opened = max(0, int(base_bugs + noise(2)))
        bugs_resolved = min(bugs_opened, max(0, int(bugs_opened * random.uniform(0.70, 0.95))))

        #Backlog grows slowly; trimmed after each release
        backlog = 85 + sprint_id * 2
        if sprint_start >= date(2024, 9, 10):
            backlog -= 18
        if sprint_start >= date(2025, 2, 18):
            backlog -= 15
        backlog = max(40, int(backlog + noise(5)))

        stories_added = max(3, int(8 + noise(3)))
        stories_completed = completed // 5

        theme = SPRINT_THEMES.get(sprint_id, f"Sprint {sprint_id} work")

        rows.append({
            "sprint_id":                 sprint_id,
            "sprint_start_date":         sprint_start,
            "sprint_end_date":           sprint_end,
            "velocity_points_planned":   planned,
            "velocity_points_completed": completed,
            "bugs_opened":               bugs_opened,
            "bugs_resolved":             bugs_resolved,
            "backlog_size":              backlog,
            "stories_added":             stories_added,
            "stories_completed":         stories_completed,
            "theme_or_focus":            theme,
        })
 
        sprint_start = sprint_end + timedelta(days=1)
        sprint_id   += 1
 
    return pd.DataFrame(rows)

def build_sprint_map(sprint_df: pd.DataFrame) -> dict:
    """Build {sprint_id: (start_date, end_date)} lookup for daily tables."""
    return{
        row.sprint_id: (row.sprint_start_date, row.sprint_end_date)
        for row in sprint_df.itertuples()
    }

def generate_daily_engagement(sprint_map: dict) -> pd.DataFrame:
    rows = []
    for d in daterange(START_DATE, END_DATE):
        wday = is_weekday(d)
        season = seasonality(d)

        release_v21 = 1.12 if d >= date(2024, 9, 10) else 1.0
        release_v25 = 1.08 if d >= date(2025, 2, 18) else 1.0
        campaign    = 1.15 if date(2024, 8, 1) <= d <= date(2024, 8, 31) else 1.0
        rate_drag   = 0.93 if d >= date(2025, 3, 5) else 1.0
 
        base_dau = 3_200 * season * release_v25 * rate_drag * (1.0 if wday else 0.45)
        dau      = max(100, int(base_dau + noise(150)))
 
        base_sessions = dau * random.uniform(1.6, 2.1) * campaign
        sessions      = max(100, int(base_sessions + noise(200)))
 
        avg_session_sec = int(max(90, 320 + noise(30) + (20 if release_v21 > 1 else 0)))
 
        base_adopt = 0.34 * release_v21 * release_v25
        feature_adoption_pct = round(min(0.85, max(0.10, base_adopt + noise(0.02))), 4)

        rows.append({
            "date":                       d,
            "daily_active_users":         dau,
            "sessions":                   sessions,
            "avg_session_duration_sec":   avg_session_sec,
            "feature_adoption_pct":       feature_adoption_pct,
            "sprint_id":                  sprint_id_for_date(d, sprint_map),
        })
    return pd.DataFrame(rows)

def generate_daily_conversion(sprint_map: dict) -> pd.DataFrame:
    rows = []
    DROP_STAGES = ["identity", "income", "docs", "review"]
 
    for d in daterange(START_DATE, END_DATE):
        wday   = is_weekday(d)
        season = seasonality(d)
 
        release_v21       = 1.10 if d >= date(2024, 9, 10) else 1.0
        campaign          = 1.18 if date(2024, 8, 1) <= d <= date(2024, 8, 31) else 1.0
        incident          = 0.45 if d == date(2024, 11, 14) else 1.0
        incident_recovery = 0.80 if date(2024, 11, 15) <= d <= date(2024, 11, 21) else 1.0
        rate_drag         = 0.88 if d >= date(2025, 3, 5) else 1.0
 
        base_started = 180 * season * campaign * rate_drag * (1.0 if wday else 0.3)
        apps_started = max(5, int(base_started + noise(15)))
 
        submit_rate = random.uniform(0.52, 0.62) * release_v21 * incident * incident_recovery
        submit_rate = min(0.82, max(0.10, submit_rate))
        apps_submitted = max(1, int(apps_started * submit_rate))
 
        approval_rate  = random.uniform(0.65, 0.72)
        apps_approved  = max(0, int(apps_submitted * approval_rate))
 
        # Drop-off stage: income was pain point pre-v2.1; review becomes bottleneck after
        if d >= date(2024, 9, 10):
            stage_weights = [0.20, 0.15, 0.35, 0.30]
        else:
            stage_weights = [0.18, 0.35, 0.30, 0.17]
        drop_off_stage = random.choices(DROP_STAGES, weights=stage_weights)[0]
 
        # Drop-off reason: incident day heavily skews docs → upload_error
        is_incident = date(2024, 11, 14) <= d <= date(2024, 11, 15)
        reason_weights = (
            DROP_OFF_REASON_WEIGHTS_INCIDENT if is_incident
            else DROP_OFF_REASON_WEIGHTS_NORMAL
        )
        drop_off_reason = random.choices(
            DROP_OFF_REASONS[drop_off_stage],
            weights=reason_weights[drop_off_stage]
        )[0]
 
        funnel_pct = round(apps_submitted / apps_started if apps_started > 0 else 0, 4)
 
        rows.append({
            "date":                    d,
            "applications_started":    apps_started,
            "applications_submitted":  apps_submitted,
            "applications_approved":   apps_approved,
            "drop_off_stage":          drop_off_stage,
            "drop_off_reason":         drop_off_reason,
            "funnel_completion_pct":   funnel_pct,
            "sprint_id":               sprint_id_for_date(d, sprint_map),
        })
    return pd.DataFrame(rows)
 
def generate_daily_satisfaction() -> pd.DataFrame:
    rows = []
    for d in daterange(START_DATE, END_DATE):
        wday = is_weekday(d)
 
        base_nps = 38
        if d >= date(2024, 9, 10):
            base_nps += 6
        if d >= date(2025, 2, 18):
            base_nps += 4
        if date(2024, 11, 14) <= d <= date(2024, 11, 28):
            base_nps -= 9
        nps_score = round(max(-30, min(80, base_nps + noise(3))), 1)
 
        base_csat = 3.8
        if d >= date(2024, 9, 10):
            base_csat += 0.20
        if d >= date(2025, 2, 18):
            base_csat += 0.15
        if date(2024, 11, 14) <= d <= date(2024, 11, 28):
            base_csat -= 0.40
        csat_score = round(max(1.0, min(5.0, base_csat + noise(0.15))), 2)
 
        base_tickets = 18 if wday else 5
        if d == date(2024, 11, 14):
            base_tickets = 210
        elif date(2024, 11, 15) <= d <= date(2024, 11, 18):
            base_tickets = 85
        elif date(2024, 11, 19) <= d <= date(2024, 11, 21):
            base_tickets = 40
 
        tickets_opened   = max(0, int(base_tickets + noise(4)))
        resolution_rate  = random.uniform(0.80, 0.96)
        tickets_resolved = min(tickets_opened, max(0, int(tickets_opened * resolution_rate)))
        avg_resolution_hours = round(
            max(1.0, 14.0 + noise(3.0) + (8 if d == date(2024, 11, 14) else 0)), 1
        )
 
        rows.append({
            "date":                     d,
            "nps_score":                nps_score,
            "csat_score":               csat_score,
            "support_tickets_opened":   tickets_opened,
            "support_tickets_resolved": tickets_resolved,
            "avg_resolution_hours":     avg_resolution_hours,
        })
    return pd.DataFrame(rows)
 
 
def generate_product_events() -> pd.DataFrame:
    return pd.DataFrame(PRODUCT_EVENTS)

# ----------------------------------------------------------------------
# Database Loader
# ----------------------------------------------------------------------  

def load_postgres(dfs: dict):
    try:
        import psycopg2
        from psycopg2.extras import execute_values  
        from psycopg2 import sql
    except ImportError:
        print("psycopg2 not found. RUN: pip install psycopg2-binary")
        return
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("Connected to PostgreSQL. \n")

    for table, df in dfs.items():
        #Truncate daily tables with Cascade to handle FK constraints cleanly
        if table in ("daily_engagement", "daily_conversion"):
            cur.execute(f"TRUNCATE TABLE {table};")
        else:
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

        cols = list(df.columns)
        values = [tuple(row) for row in df.itertuples(index=False, name=None)]
        insert = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
          sql.Identifier(table),
          sql.SQL(', ').join(map(sql.Identifier, cols))
        )
        execute_values(cur, insert, values)
        print(f" Loaded {len(values):,} rows -> {table}")

    conn.commit()
    cur.close()
    conn.close()
    print("\n PostgreSQL load complete. Database: mortgage_portal_kpi")

# ----------------------------------------------------------------------
# Main Execution  
# ----------------------------------------------------------------------

def main():
    print("Generating mock data…\n")
 
    # sprint_metrics must be generated first — daily tables use its date ranges
    sprint_df  = generate_sprint_metrics()
    sprint_map = build_sprint_map(sprint_df)
 
    dfs = {
        "sprint_metrics":     sprint_df,
        "product_events":     generate_product_events(),
        "daily_engagement":   generate_daily_engagement(sprint_map),
        "daily_conversion":   generate_daily_conversion(sprint_map),
        "daily_satisfaction": generate_daily_satisfaction(),
    }
 
    total_rows = sum(len(df) for df in dfs.values())
    for name, df in dfs.items():
        print(f"  {name}: {len(df):,} rows | cols: {list(df.columns)}")
    print(f"\n  Total: {total_rows:,} rows across {len(dfs)} tables.\n")
 
    load_postgres(dfs)
 
 
if __name__ == "__main__":
    main()