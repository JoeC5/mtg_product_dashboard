# Mortgage Origination Portal — KPI Data Dictionary

**Database:** `mortgage_portal_kpi` &nbsp;|&nbsp; **Version:** 1.0 &nbsp;|&nbsp; **Generated:** June 2025

---

## Purpose & Scope

This data dictionary documents all tables, fields, data types, and business definitions for the `mortgage_portal_kpi` PostgreSQL database. The database supports a KPI dashboard that tracks the performance of a mortgage origination portal across four dimensions: user engagement, application conversion, customer satisfaction, and agile delivery health.

The data covers 12 months of daily snapshots (June 1, 2024 through May 31, 2025) plus sprint-level metrics across 27 two-week sprints. All data is synthetic and generated for portfolio and demonstration purposes.

---

## Database Overview

| Table | Rows | Description |
|---|---|---|
| `daily_engagement` | 365 | One row per calendar day. Tracks user activity and feature usage on the portal. |
| `daily_conversion` | 365 | One row per calendar day. Tracks the mortgage application funnel from start to approval. |
| `daily_satisfaction` | 365 | One row per calendar day. Tracks NPS, CSAT, and support ticket volume. |
| `sprint_metrics` | 27 | One row per two-week sprint. Tracks agile delivery velocity, bug rates, and backlog health. |
| `product_events` | 5 | Sparse event log of significant product moments: releases, incidents, campaigns, rate changes. |

---

## Table Relationships

`sprint_metrics` is the parent table. `daily_engagement` and `daily_conversion` each contain a `sprint_id` foreign key that references `sprint_metrics.sprint_id`. This allows daily user behavior metrics to be joined to the sprint context in which they occurred — enabling analysis of whether specific sprint themes drove measurable changes in engagement or conversion.

`daily_satisfaction` and `product_events` have no foreign key dependencies and stand alone.

---

## Table Definitions

### 1. `daily_engagement`

Captures daily user activity on the mortgage origination portal. Each row represents one calendar day. Weekend values are approximately 45% of weekday baselines, reflecting lower consumer mortgage activity on non-business days. Values are influenced by seasonal mortgage demand, product releases, and marketing campaigns.

| Field | Type | Description | Example | Business Notes |
|---|---|---|---|---|
| `date` | DATE (PK) | The calendar date of the snapshot. Primary key — one row per day. | 2024-08-15 | Used as the primary join key across all daily tables. |
| `daily_active_users` | INTEGER | Count of unique users who visited the portal on this date. | 3,847 | Baseline ~3,200 on weekdays at peak season. Influenced by seasonality, releases, and campaigns. |
| `sessions` | INTEGER | Total number of sessions initiated on this date. A single user may generate multiple sessions. | 7,204 | Ratio of sessions to DAU typically ranges from 1.6x to 2.1x. |
| `avg_session_duration_sec` | INTEGER | Average session length in seconds across all sessions on this date. | 338 | Proxy for engagement depth. Increased slightly after v2.1 release due to UX improvements. |
| `feature_adoption_pct` | NUMERIC(6,4) | Proportion of DAU who engaged with at least one key product feature. | 0.4217 | Scale: 0.00 to 1.00. Rose after each product release as new features were introduced. |
| `sprint_id` | INTEGER (FK) | Foreign key referencing `sprint_metrics.sprint_id`. | 7 | Enables correlation of daily engagement trends with sprint theme and work delivered. |

---

### 2. `daily_conversion`

Tracks the mortgage application funnel on a daily basis, from initial application start through submission and approval. Also captures the point and reason for user abandonment, enabling causal analysis of funnel drop-off. Application volume is strongly influenced by mortgage rate environment, seasonal homebuying demand, and portal performance.

| Field | Type | Description | Example | Business Notes |
|---|---|---|---|---|
| `date` | DATE (PK) | The calendar date of the snapshot. Primary key — one row per day. | 2024-09-22 | Join key to other daily tables and to `product_events` for event annotation. |
| `applications_started` | INTEGER | Number of mortgage applications initiated on this date — top of funnel. | 187 | Baseline ~180 on peak weekdays. Suppressed ~12% after March 2025 rate increase. |
| `applications_submitted` | INTEGER | Number of applications fully completed and submitted on this date. | 112 | Submission rate typically 52–82%. Improved after v2.1; dropped sharply during Nov 2024 outage. |
| `applications_approved` | INTEGER | Number of submitted applications that received an approval decision. | 76 | Approval rate stable at 65–72% of submissions, reflecting underwriting criteria. |
| `drop_off_stage` | VARCHAR(20) | Funnel stage where users most commonly abandoned on this date. | docs | Values: `identity` \| `income` \| `docs` \| `review`. Pre-v2.1: income dominated. Post-v2.1: docs and review. |
| `drop_off_reason` | VARCHAR(50) | Most common specific reason for abandonment at the reported stage. | upload_error | Values: `ssn_validation_failed`, `income_threshold_not_met`, `upload_error`, `file_size_exceeded`, `user_abandoned`, `session_timeout`, `returned_later`, `application_expired`, `rate_lock_expired`. |
| `funnel_completion_pct` | NUMERIC(6,4) | Ratio of `applications_submitted` to `applications_started`. | 0.5989 | Key headline conversion metric. Target range: 0.60–0.75 under normal conditions. |
| `sprint_id` | INTEGER (FK) | Foreign key referencing `sprint_metrics.sprint_id`. | 8 | Allows conversion to be segmented by sprint theme. |

---

### 3. `daily_satisfaction`

Captures daily customer satisfaction signals and support volume. NPS and CSAT scores reflect survey responses collected from portal users and lag real events by approximately one to two weeks. Support ticket volume is a leading indicator — it spikes immediately when something goes wrong, while NPS and CSAT reflect the downstream sentiment impact.

| Field | Type | Description | Example | Business Notes |
|---|---|---|---|---|
| `date` | DATE (PK) | The calendar date of the snapshot. Primary key — one row per day. | 2024-11-14 | Nov 14, 2024 is a key inflection point — tickets spike immediately, NPS/CSAT follow over two weeks. |
| `nps_score` | NUMERIC(5,1) | Net Promoter Score for this date. Range: -100 to +100. | 42.3 | Baseline ~38. Benchmarks: below 0 = poor, 0–30 = good, 30–70 = great, 70+ = excellent. |
| `csat_score` | NUMERIC(4,2) | Customer Satisfaction score on a 1–5 scale. | 4.12 | Baseline ~3.8. A score below 3.5 warrants immediate investigation. |
| `support_tickets_opened` | INTEGER | Number of new support tickets submitted on this date. | 207 | Baseline ~18 weekdays, ~5 weekends. Spiked to ~207 on the Nov 2024 incident date. |
| `support_tickets_resolved` | INTEGER | Number of support tickets closed or resolved on this date. | 164 | Resolution rate typically 80–96%. A widening gap signals backlog buildup. |
| `avg_resolution_hours` | NUMERIC(5,1) | Average time in hours to resolve a support ticket. | 16.4 | Baseline ~14 hours. High volume with low resolution hours indicates effective triage. |

---

### 4. `sprint_metrics`

Tracks agile delivery health across 27 two-week sprints covering the full 12-month period. Each sprint is associated with a named theme or focus area, enabling correlation between delivery work and user-facing metric changes.

| Field | Type | Description | Example | Business Notes |
|---|---|---|---|---|
| `sprint_id` | INTEGER (PK) | Unique sequential identifier. Sprints numbered 1–27. | 12 | Referenced as FK in `daily_engagement` and `daily_conversion`. |
| `sprint_start_date` | DATE | First day of the sprint. | 2024-11-05 | Sprints run on a strict 14-day cadence with no gaps. |
| `sprint_end_date` | DATE | Last day of the sprint. | 2024-11-18 | Sprint 12 covers the Nov 14 incident date, explaining the velocity dip and bug spike. |
| `velocity_points_planned` | INTEGER | Story points committed at sprint planning. | 52 | Ramps from ~31 in Sprint 1 to ~52 at plateau. |
| `velocity_points_completed` | INTEGER | Story points completed and accepted by end of sprint. | 44 | Completion rate typically 78–97% of planned. |
| `bugs_opened` | INTEGER | New bug tickets opened during the sprint. | 22 | Baseline ~6 per sprint. Spiked to ~22 in incident sprint. |
| `bugs_resolved` | INTEGER | Bug tickets resolved and closed during the sprint. | 17 | Resolution rate typically 70–95%. Below 70% signals backlog accumulation. |
| `backlog_size` | INTEGER | Total backlog items at end of sprint. | 94 | Grows ~2 items per sprint organically. Trimmed after each major release. |
| `stories_added` | INTEGER | New user stories added to the backlog during the sprint. | 9 | Compared to `stories_completed` to assess whether team keeps pace with demand. |
| `stories_completed` | INTEGER | User stories completed and accepted during the sprint. | 9 | Used alongside velocity for a dual view of throughput. |
| `theme_or_focus` | VARCHAR(100) | Plain-English description of the sprint's primary goal. | Income documentation UI improvements | Provides narrative context for metric changes. |

---

### 5. `product_events`

A sparse event log capturing five significant product moments over the 12-month period. These events are used to annotate charts in the dashboard and provide context when explaining anomalies or inflection points in the data.

| Field | Type | Description | Example | Business Notes |
|---|---|---|---|---|
| `id` | SERIAL (PK) | Auto-incrementing unique identifier. | 3 | System-generated. No business significance beyond uniqueness. |
| `date` | DATE | The date on which the product event occurred. | 2024-11-14 | Used to annotate daily metric charts. |
| `event_type` | VARCHAR(30) | Category of the event. | incident | Values: `release` \| `incident` \| `campaign` \| `rate_change`. |
| `description` | TEXT | Plain-English narrative describing the event and its expected impact. | P1 outage — document upload service down for ~6 hours. Support ticket spike expected. NPS impact ~-8 pts over 2 weeks. | Written at PM level — describes business impact, not just technical facts. |

---

## Key Events Reference

| Date | Type | Event | Expected Metric Impact |
|---|---|---|---|
| Aug 1, 2024 | Campaign | Summer homebuyer campaign | Sessions +15%, applications started +18% through August |
| Sep 10, 2024 | Release | v2.1 launch | Funnel conversion +10%, feature adoption +12%, NPS +6 pts |
| Nov 14, 2024 | Incident | P1 upload outage | Applications submitted -55%, tickets opened +1,000%, NPS -9 pts over 2 weeks |
| Feb 18, 2025 | Release | v2.5 launch | DAU +8%, feature adoption lifts, NPS +4 pts, mobile engagement improves |
| Mar 5, 2025 | Rate change | 30-yr fixed crosses 7.5% | Applications started -12%, DAU -7%, funnel volume suppressed through May 2025 |

---

## Data Generation Notes

**Seasonality:** Mortgage origination demand follows a realistic annual curve. Spring (March–June) is peak season at 1.25–1.30× baseline. Winter (December–February) slows to 0.70–0.75× baseline.

**Weekend suppression:** Daily active users and application starts are approximately 45% and 30% of weekday values respectively on weekends.

**Random noise:** All metrics include normally distributed random noise to simulate real-world variation. Engagement metrics use a standard deviation of ~150 users; conversion metrics use ~15 applications.

**Reproducibility:** All random number generation uses fixed seeds (`random.seed(42)`, `np.random.seed(42)`), ensuring the dataset is identical on every run of the generation script.

---

*`mortgage_portal_kpi` — Data Dictionary v1.0 — Generated June 2025*
