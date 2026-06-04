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
 
import random
from datetime import date, timedelta
 
import numpy as np
import pandas as pd

