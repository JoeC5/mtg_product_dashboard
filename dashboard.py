"""
dashboard.py
------------
Streamlit KPI Dashboard — Mortgage Origination Portal
Database: mortgage_portal_kpi (PostgreSQL)
 
USAGE:
    streamlit run dashboard.py
 
SECTIONS:
    0. Sidebar     — date filters + key metric scorecards
    1. Engagement  — DAU, sessions, feature adoption
    2. Conversion  — funnel metrics, drop-off analysis
    3. Satisfaction — NPS, CSAT, support tickets
    4. Delivery    — sprint velocity, bugs, backlog
"""

import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Mortgage Portal KPI Dashboard",
    page_icon="🏠",
    layout="wide",
)

#----------------------------------------------------------------------
# Color Palette - (colorblind-friendly)
#----------------------------------------------------------------------

BLUE       = "#2E75B6"
NAVY       = "#1F4E79"
TEAL       = "#00838F"
AMBER      = "#E6A817"
RED        = "#C0392B"
GREEN      = "#27AE60"
LIGHT_GREY = "#F4F6F8"
 
EVENT_COLORS = {
    "release":     GREEN,
    "incident":    RED,
    "campaign":    AMBER,
    "rate_change": TEAL,
}
 
 #----------------------------------------------------------------------
 # DB Connection
 #----------------------------------------------------------------------

# @st.cache_resource
# def get_connection():
    # import psycopg2
        # return psycopg2.connect(
        # host=os.getenv("DB_HOST", "localhost"),
        # port=int(os.getenv("DB_PORT", 5432)),
        # dbname=os.getenv("DB_NAME", "mortgage_portal_kpi"),
        # user=os.getenv("DB_USER", "postgres"),
        # password=os.getenv("DB_PASSWORD", ""),
   #  )

@st.cache_resource
def get_connection():
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "mortgage_portal_kpi"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


@st.cache_data(ttl=300)
def query(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    except Exception as e:
         conn.rollback()
         raise e


#----------------------------------------------------------------------
# Data Loaders
#----------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_engagement(start: date, end: date) -> pd.DataFrame:
    return query(
        """
        SELECT e.date, e.daily_active_users, e.sessions,
               e.avg_session_duration_sec, e.feature_adoption_pct,
               e.sprint_id, s.theme_or_focus
        FROM daily_engagement e
        LEFT JOIN sprint_metrics s USING (sprint_id)
        WHERE e.date BETWEEN %s AND %s
        ORDER BY e.date
        """,
        (start, end)
    )

@st.cache_data(ttl=300)
def load_conversion(start: date, end: date) -> pd.DataFrame:
    return query(
        """
        SELECT c.date, c.applications_started, c.applications_submitted,
               c.applications_approved, c.drop_off_stage, c.drop_off_reason,
               c.funnel_completion_pct, c.sprint_id, s.theme_or_focus
        FROM daily_conversion c
        LEFT JOIN sprint_metrics s USING (sprint_id)
        WHERE c.date BETWEEN %s AND %s
        ORDER BY c.date
        """,
        (start, end)
    )

@st.cache_data(ttl=300)
def load_satisfaction(start: date, end: date) -> pd.DataFrame:
    return query(
        """
        SELECT date, nps_score, csat_score,
               support_tickets_opened, support_tickets_resolved,
               avg_resolution_hours
        FROM daily_satisfaction
        WHERE date BETWEEN %s AND %s
        ORDER BY date
        """,
        (start, end),
    )

@st.cache_data(ttl=300)
def load_sprints(start: date, end: date) -> pd.DataFrame:
    return query(
        """
        SELECT sprint_id, sprint_start_date, sprint_end_date,
               velocity_points_planned, velocity_points_completed,
               bugs_opened, bugs_resolved, backlog_size,
               stories_added, stories_completed, theme_or_focus
        FROM sprint_metrics
        WHERE sprint_end_date >= %s AND sprint_start_date <= %s
        ORDER BY sprint_id
        """,
        (start, end),
    )

@st.cache_data(ttl=300)
def load_events(start: date, end: date) -> pd.DataFrame:
    return query(
        """
        SELECT date, event_type, description
        FROM product_events
        WHERE date BETWEEN %s AND %s
        ORDER BY date
        """,
        (start, end),
    )

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def add_event_lines(fig: go.Figure, events: pd.DataFrame) -> go.Figure:
    """Overlay vertical event annotations on a Plotly figure."""
    for _, ev in events.iterrows():
        color = EVENT_COLORS.get(ev["event_type"], NAVY)
        fig.add_vline(
            x=str(ev["date"]),
            line_width=1.5,
            line_dash="dash",
            line_color=color,
            annotation_text=ev["event_type"],
            annotation_position="top left",
            annotation_font_size=10,
            annotation_font_color=color,
        )
    return fig

def scorecard(label: str, value: str, delta: str = None, delta_color: str = "normal"):
    """Render a single metric scorecard using st.metric."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)

def section_header(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"<p style='color:#595959; margin-top:-12px;'>{subtitle}</p>",
                    unsafe_allow_html=True)
    st.markdown("---")

def weekly(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Resample a daily DataFrame to weekly averages for cleaner trend lines."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    return df.set_index(date_col).resample("W").mean(numeric_only=True).reset_index()

#----------------------------------------------------------------------
#SideBar - Filters
#----------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/cottage.png", width=60)
    st.title("Mortgage Portal")
    st.markdown("**KPI Dashboard**")
    st.markdown("---")
 
    st.subheader("📅 Date Filter")
 
    # Quick-select preset
    preset = st.selectbox(
        "Quick select",
        ["Full year", "Last 90 days", "Last 60 days", "Last 30 days", "Custom range"],
    )
 
    DATA_END   = date(2025, 5, 31)
    DATA_START = date(2024, 6, 1)

    if preset == "Full year":
            default_start, default_end = DATA_START, DATA_END
    elif preset == "Last 90 days":
            default_start, default_end = DATA_END - timedelta(days=90), DATA_END
    elif preset == "Last 60 days":
            default_start, default_end = DATA_END - timedelta(days=60), DATA_END
    elif preset == "Last 30 days":
            default_start, default_end = DATA_END - timedelta(days=30), DATA_END
    else:
            default_start, default_end = DATA_START, DATA_END

     # Custom date pickers (always visible; pre-filled from preset)
    start_date = st.date_input("From", value=default_start,
                               min_value=DATA_START, max_value=DATA_END)
    end_date   = st.date_input("To",   value=default_end,
                               min_value=DATA_START, max_value=DATA_END)
 
    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()
 
    st.markdown("---")
    st.subheader("🏷️ Event Legend")
    for etype, color in EVENT_COLORS.items():
        st.markdown(
            f"<span style='color:{color}; font-weight:bold;'>— {etype.replace('_',' ').title()}</span>",
            unsafe_allow_html=True,
        )
    st.markdown("---")
    st.caption(f"Data range: {DATA_START} → {DATA_END}")
    st.caption("Synthetic data for portfolio demonstration.")

# ──────────────────────────────────────────────
#  LOAD DATA
# ──────────────────────────────────────────────
with st.spinner("Loading data…"):
    eng  = load_engagement(start_date, end_date)
    conv = load_conversion(start_date, end_date)
    sat  = load_satisfaction(start_date, end_date)
    spr  = load_sprints(start_date, end_date)
    evts = load_events(start_date, end_date)
 
eng["date"]  = pd.to_datetime(eng["date"])
conv["date"] = pd.to_datetime(conv["date"])
sat["date"]  = pd.to_datetime(sat["date"])
 
# ──────────────────────────────────────────────
#  PAGE TITLE
# ──────────────────────────────────────────────
st.title("🏡 Mortgage Origination Portal — KPI Dashboard")
st.markdown(
    f"Showing **{start_date.strftime('%b %d, %Y')}** to **{end_date.strftime('%b %d, %Y')}** "
    f"— {(end_date - start_date).days + 1} days"
)
st.markdown("---")
     
# ══════════════════════════════════════════════
#  SECTION 0 — HEADLINE SCORECARDS
# ══════════════════════════════════════════════
st.markdown("### 📊 Headline Metrics")
 
col1, col2, col3, col4, col5 = st.columns(5)
 
avg_dau          = int(eng["daily_active_users"].mean())
avg_funnel       = f"{conv['funnel_completion_pct'].mean()*100:.1f}%"
avg_nps          = f"{sat['nps_score'].mean():.1f}"
#avg_csat         = f"{sat['csat_score'].mean():.2f}"
avg_csat_raw = sat['csat_score'].mean()
csat_pct = (sat['csat_score'] >= 4).sum() / len(sat) * 100
avg_csat = f"{avg_csat_raw:.2f} / 5  ({csat_pct:.0f}% sat)"
avg_velocity_pct = f"{(spr['velocity_points_completed'] / spr['velocity_points_planned']).mean()*100:.0f}%"
 
with col1: scorecard("Avg Daily Active Users", f"{avg_dau:,}")
with col2: scorecard("Avg Funnel Completion", avg_funnel)
with col3: scorecard("Avg NPS Score", avg_nps)
with col4: scorecard("CSAT Score (Avg/ % Satisfied)", avg_csat)
with col5: scorecard("Sprint Completion Rate", avg_velocity_pct)
 
st.markdown("---")     

# ══════════════════════════════════════════════
#  SECTION 1 — ENGAGEMENT
# ════════════════════════════════════════════
section_header("👥 User Engagement", "Daily active users, session volume, and feature adoption")
 
# ── 1a: DAU trend ──────────────────────────────
st.markdown("#### Daily Active Users")
eng_weekly = weekly(eng)
 
fig_dau = px.line(
    eng_weekly, x="date", y="daily_active_users",
    labels={"date": "Date", "daily_active_users": "Daily Active Users"},
    color_discrete_sequence=[BLUE],
    template="plotly_white",
)
fig_dau.update_traces(line_width=2)
fig_dau = add_event_lines(fig_dau, evts)
fig_dau.update_layout(hovermode="x unified", margin=dict(t=20))
st.plotly_chart(fig_dau, use_container_width=True)
 
# ── 1b: Sessions + Avg session duration ────────
col_a, col_b = st.columns(2)
 
with col_a:
    st.markdown("#### Weekly Sessions")
    fig_sess = px.area(
        eng_weekly, x="date", y="sessions",
        labels={"date": "Date", "sessions": "Sessions"},
        color_discrete_sequence=[TEAL],
        template="plotly_white",
    )
    fig_sess = add_event_lines(fig_sess, evts)
    fig_sess.update_layout(hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig_sess, use_container_width=True)
 
with col_b:
    st.markdown("#### Avg Session Duration (seconds)")
    fig_dur = px.line(
        eng_weekly, x="date", y="avg_session_duration_sec",
        labels={"date": "Date", "avg_session_duration_sec": "Seconds"},
        color_discrete_sequence=[NAVY],
        template="plotly_white",
    )
    fig_dur = add_event_lines(fig_dur, evts)
    fig_dur.update_layout(hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig_dur, use_container_width=True)
 
# ── 1c: Feature adoption ───────────────────────
st.markdown("#### Feature Adoption Rate (% of DAU using key features)")
fig_adopt = px.line(
    eng_weekly, x="date", y="feature_adoption_pct",
    labels={"date": "Date", "feature_adoption_pct": "Adoption Rate"},
    color_discrete_sequence=[AMBER],
    template="plotly_white",
)
fig_adopt.update_traces(line_width=2)
fig_adopt.update_yaxes(tickformat=".0%")
fig_adopt = add_event_lines(fig_adopt, evts)
fig_adopt.update_layout(hovermode="x unified", margin=dict(t=20))
st.plotly_chart(fig_adopt, use_container_width=True)
 
st.markdown("---")

# ══════════════════════════════════════════════
#  SECTION 2 — CONVERSION
# ══════════════════════════════════════════════
section_header("🔄 Application Conversion", "Funnel performance, drop-off stage and reason analysis")
 
# ── 2a: Funnel completion trend ─────────────────
st.markdown("#### Funnel Completion Rate (Weekly Avg)")
conv_weekly = weekly(conv)
 
fig_funnel = px.line(
    conv_weekly, x="date", y="funnel_completion_pct",
    labels={"date": "Date", "funnel_completion_pct": "Completion Rate"},
    color_discrete_sequence=[GREEN],
    template="plotly_white",
)
fig_funnel.update_traces(line_width=2)
fig_funnel.update_yaxes(tickformat=".0%")
fig_funnel = add_event_lines(fig_funnel, evts)
fig_funnel.update_layout(hovermode="x unified", margin=dict(t=20))
st.plotly_chart(fig_funnel, use_container_width=True)
 
# ── 2b: Application volume waterfall ────────────
st.markdown("#### Application Volume — Funnel Stages (Period Total)")
totals = {
    "Started":   int(conv["applications_started"].sum()),
    "Submitted": int(conv["applications_submitted"].sum()),
    "Approved":  int(conv["applications_approved"].sum()),
}
fig_wf = go.Figure(go.Funnel(
    y=list(totals.keys()),
    x=list(totals.values()),
    textinfo="value+percent initial",
    marker_color=[BLUE, TEAL, GREEN],
))
fig_wf.update_layout(template="plotly_white", margin=dict(t=20))
st.plotly_chart(fig_wf, use_container_width=True)
 
# ── 2c: Drop-off stage + reason ─────────────────
col_c, col_d = st.columns(2)
 
with col_c:
    st.markdown("#### Drop-off Stage Distribution")
    stage_counts = conv["drop_off_stage"].value_counts().reset_index()
    stage_counts.columns = ["Stage", "Count"]
    fig_stage = px.bar(
        stage_counts, x="Stage", y="Count",
        color="Stage",
        color_discrete_sequence=[BLUE, TEAL, AMBER, NAVY],
        template="plotly_white",
    )
    fig_stage.update_layout(showlegend=False, margin=dict(t=20))
    st.plotly_chart(fig_stage, use_container_width=True)
 
with col_d:
    st.markdown("#### Drop-off Reason Distribution")
    reason_counts = conv["drop_off_reason"].value_counts().reset_index()
    reason_counts.columns = ["Reason", "Count"]
    fig_reason = px.bar(
        reason_counts, x="Count", y="Reason",
        orientation="h",
        color_discrete_sequence=[TEAL],
        template="plotly_white",
    )
    fig_reason.update_layout(showlegend=False, margin=dict(t=20))
    st.plotly_chart(fig_reason, use_container_width=True)
 
# ── 2d: Daily application volume trend ──────────
st.markdown("#### Daily Application Volume (Started vs Submitted)")
fig_apps = go.Figure()
fig_apps.add_trace(go.Scatter(
    x=conv_weekly["date"], y=conv_weekly["applications_started"],
    name="Started", line=dict(color=BLUE, width=2), mode="lines",
))
fig_apps.add_trace(go.Scatter(
    x=conv_weekly["date"], y=conv_weekly["applications_submitted"],
    name="Submitted", line=dict(color=GREEN, width=2), mode="lines",
))
fig_apps.update_layout(
    template="plotly_white", hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(t=20),
)
fig_apps = add_event_lines(fig_apps, evts)
st.plotly_chart(fig_apps, use_container_width=True)
 
st.markdown("---")
 
 # ══════════════════════════════════════════════
#  SECTION 3 — SATISFACTION
# ══════════════════════════════════════════════
section_header("⭐ Customer Satisfaction", "NPS, CSAT, and support ticket trends")
 
# ── 3a: NPS trend ──────────────────────────────
st.markdown("#### Net Promoter Score (NPS) — Weekly Avg")
sat_weekly = weekly(sat)
 
fig_nps = px.line(
    sat_weekly, x="date", y="nps_score",
    labels={"date": "Date", "nps_score": "NPS Score"},
    color_discrete_sequence=[NAVY],
    template="plotly_white",
)
fig_nps.update_traces(line_width=2)
fig_nps.add_hline(y=0,  line_dash="dot", line_color="red",   annotation_text="0 (neutral)")
fig_nps.add_hline(y=30, line_dash="dot", line_color="green", annotation_text="30 (good)")
fig_nps = add_event_lines(fig_nps, evts)
fig_nps.update_layout(hovermode="x unified", margin=dict(t=20))
st.plotly_chart(fig_nps, use_container_width=True)
 
# ── 3b: CSAT + support tickets ──────────────────
col_e, col_f = st.columns(2)
 
with col_e:
    st.markdown("#### CSAT Score — Weekly Avg (1–5 scale)")
    fig_csat = px.line(
        sat_weekly, x="date", y="csat_score",
        labels={"date": "Date", "csat_score": "CSAT Score"},
        color_discrete_sequence=[TEAL],
        template="plotly_white",
    )
    fig_csat.update_traces(line_width=2)
    fig_csat.update_yaxes(range=[1, 5])
    fig_csat.add_hline(y=3.5, line_dash="dot", line_color="orange",
                       annotation_text="3.5 threshold")
    fig_csat = add_event_lines(fig_csat, evts)
    fig_csat.update_layout(hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig_csat, use_container_width=True)
 
with col_f:
    st.markdown("#### Support Tickets — Opened vs Resolved (Weekly)")
    fig_tix = go.Figure()
    fig_tix.add_trace(go.Bar(
        x=sat_weekly["date"], y=sat_weekly["support_tickets_opened"],
        name="Opened", marker_color=RED,
    ))
    fig_tix.add_trace(go.Bar(
        x=sat_weekly["date"], y=sat_weekly["support_tickets_resolved"],
        name="Resolved", marker_color=GREEN,
    ))
    fig_tix.update_layout(
        barmode="group", template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified", margin=dict(t=20),
    )
    st.plotly_chart(fig_tix, use_container_width=True)
 
# ── 3c: Avg resolution hours ────────────────────
st.markdown("#### Avg Support Ticket Resolution Time (hours) — Weekly Avg")
fig_res = px.area(
    sat_weekly, x="date", y="avg_resolution_hours",
    labels={"date": "Date", "avg_resolution_hours": "Hours"},
    color_discrete_sequence=[AMBER],
    template="plotly_white",
)
fig_res = add_event_lines(fig_res, evts)
fig_res.update_layout(hovermode="x unified", margin=dict(t=20))
st.plotly_chart(fig_res, use_container_width=True)
 
st.markdown("---")

# ══════════════════════════════════════════════
#  SECTION 4 — DELIVERY
# ══════════════════════════════════════════════
section_header("🚀 Agile Delivery Health", "Sprint velocity, bug rates, and backlog trend")
 
if spr.empty:
    st.info("No sprint data available for the selected date range.")
else:
    spr["sprint_label"] = spr["sprint_id"].apply(lambda x: f"S{x}")
    spr["completion_pct"] = (
        spr["velocity_points_completed"] / spr["velocity_points_planned"] * 100
    ).round(1)
 
    # ── 4a: Velocity — planned vs completed ─────
    st.markdown("#### Sprint Velocity — Planned vs Completed (story points)")
    fig_vel = go.Figure()
    fig_vel.add_trace(go.Bar(
        x=spr["sprint_label"], y=spr["velocity_points_planned"],
        name="Planned", marker_color=LIGHT_GREY,
        marker_line_color=NAVY, marker_line_width=1,
    ))
    fig_vel.add_trace(go.Bar(
        x=spr["sprint_label"], y=spr["velocity_points_completed"],
        name="Completed", marker_color=BLUE,
    ))
    fig_vel.update_layout(
        barmode="overlay", template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        hovermode="x unified", margin=dict(t=20),
    )
    st.plotly_chart(fig_vel, use_container_width=True)
 
    # ── 4b: Bugs + Backlog ──────────────────────
    col_g, col_h = st.columns(2)
 
    with col_g:
        st.markdown("#### Bug Volume per Sprint — Opened vs Resolved")
        fig_bugs = go.Figure()
        fig_bugs.add_trace(go.Bar(
            x=spr["sprint_label"], y=spr["bugs_opened"],
            name="Opened", marker_color=RED,
        ))
        fig_bugs.add_trace(go.Bar(
            x=spr["sprint_label"], y=spr["bugs_resolved"],
            name="Resolved", marker_color=GREEN,
        ))
        fig_bugs.update_layout(
            barmode="group", template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            hovermode="x unified", margin=dict(t=20),
        )
        st.plotly_chart(fig_bugs, use_container_width=True)
 
    with col_h:
        st.markdown("#### Backlog Size Over Time")
        fig_bl = px.line(
            spr, x="sprint_label", y="backlog_size",
            labels={"sprint_label": "Sprint", "backlog_size": "Items"},
            color_discrete_sequence=[AMBER],
            markers=True,
            template="plotly_white",
        )
        fig_bl.update_layout(hovermode="x unified", margin=dict(t=20))
        st.plotly_chart(fig_bl, use_container_width=True)
 
    # ── 4c: Sprint detail table ─────────────────
    st.markdown("#### Sprint Detail")
    display_cols = [
        "sprint_label", "sprint_start_date", "sprint_end_date",
        "theme_or_focus", "velocity_points_planned", "velocity_points_completed",
        "completion_pct", "bugs_opened", "bugs_resolved", "backlog_size",
    ]
    col_labels = {
        "sprint_label":              "Sprint",
        "sprint_start_date":         "Start",
        "sprint_end_date":           "End",
        "theme_or_focus":            "Theme / Focus",
        "velocity_points_planned":   "Planned Pts",
        "velocity_points_completed": "Completed Pts",
        "completion_pct":            "Completion %",
        "bugs_opened":               "Bugs Opened",
        "bugs_resolved":             "Bugs Resolved",
        "backlog_size":              "Backlog Size",
    }
    st.dataframe(
        spr[display_cols].rename(columns=col_labels),
        use_container_width=True,
        hide_index=True,
    )
 
# ──────────────────────────────────────────────
#  FOOTER
# ──────────────────────────────────────────────
st.markdown("---")
st.caption(
    "Mortgage Portal KPI Dashboard — synthetic data for portfolio demonstration. "
    "Built with Streamlit + Plotly + PostgreSQL."
)
 