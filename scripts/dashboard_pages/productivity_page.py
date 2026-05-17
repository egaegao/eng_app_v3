import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# ==========================================
# GLOBAL CONFIGURATIONS & CONSTANTS
# ==========================================
FONT_FAMILY = "Segoe UI, Arial, sans-serif"

# ==========================================
# CACHED CHART BUILDERS (OPTIMIZATION)
# ==========================================

@st.cache_data(show_spinner=False)
def build_fig_cat_cached(df_melt, x_col):
    fig = px.bar(
        df_melt,
        x=x_col,
        y="value",
        color="series",
        barmode="group",
        text=df_melt["value"].round(1),
        template="plotly_white",
        color_discrete_map={"actual": "#2563eb", "plan": "#64748b"}
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(size=14, color="#000000", family="Inter"),
        marker=dict(opacity=0.95)
    )
    fig.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=55, b=20),
        legend_title_text="",
        bargap=0.28,
        font=dict(family="Inter", size=14, color="#000000"),
        xaxis=dict(tickfont=dict(size=15, color="#000000"), title=""),
        yaxis=dict(tickfont=dict(size=15, color="#000000"), gridcolor="#e5e7eb")
    )
    return fig

@st.cache_data(show_spinner=False)
def build_trend_prod_cached(df_trend, x_col):
    fig = px.line(
        df_trend, x=x_col, y=["actual", "plan"],
        markers=True, template="plotly_white",
        color_discrete_map={"actual": "#2563eb", "plan": "#64748b"}
    )
    fig.update_traces(line_shape="spline", line=dict(width=4), marker=dict(size=10))
    fig.update_traces(patch={"line": {"dash": "dot", "width": 3}}, selector={"name": "plan"})

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Actual: %{customdata[1]}<extra></extra>",
        customdata=df_trend[["label", "actual_fmt"]],
        selector={"name": "actual"}
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Plan: %{customdata[1]}<extra></extra>",
        customdata=df_trend[["label", "plan_fmt"]],
        selector={"name": "plan"}
    )

    fig.update_xaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor='#e5e7eb', 
        griddash='dot',
        tickmode="array", 
        tickvals=df_trend[x_col], 
        ticktext=df_trend["label"], 
        tickangle=0, 
        tickfont=dict(size=16, color="#000000", family="Inter", weight=700),
        title=""
    )
    
    fig.update_yaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor='#e5e7eb',
        tickfont=dict(size=15, color="#000000", family="Inter"),
        title_text="Productivity",
        title_font=dict(size=16, color="#000000", family="Inter")
    )

    fig.update_layout(
        height=400, 
        margin=dict(l=50, r=20, t=40, b=70),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=14, color="black")),
        font=dict(family="Inter", size=12, color="black"),
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Inter", font_color="black", bordercolor="#e5e7eb"),
        hovermode="x unified"
    )
    return fig

@st.cache_data(show_spinner=False)
def build_snapshot_prod_cached(chart_df, title):
    fig = px.bar(
        chart_df, x="Type", y="Value", text="Value", 
        color="Type", color_discrete_map={"Actual": "#2563eb", "Plan": "#94a3b8"},
        template="plotly_white", title=title
    )
    fig.update_traces(
        texttemplate='%{text:.1f}',
        textposition='outside',
        textfont=dict(size=18, color="black", family="Inter")
    )
    fig.update_layout(
        height=320,
        yaxis=dict(range=[0, chart_df["Value"].max() * 1.4], tickfont=dict(size=14, color="black")),
        xaxis=dict(tickfont=dict(size=16, color="black")),
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
        font=dict(family="Inter")
    )
    return fig

# ==========================================
# REVISED FORMATTING FUNCTIONS
# ==========================================

def fmt_num(x, unit=None):
    if pd.isna(x):
        return "-"
    value = f"{x:.1f}"
    return f"{value} {unit}" if unit else value

def fmt_variance(x, unit=None):
    if pd.isna(x):
        return "-"
    color = "#047857" if x >= 0 else "#dc2626"
    sign = "+" if x >= 0 else ""
    value = f"{sign}{x:.1f}"
    if unit:
        value = f"{value} {unit}"
    return f"<span style='color:{color};'>{value}</span>"

def fmt_achievement(x):
    if pd.isna(x):
        return "-"
    color = "#047857" if x >= 100 else "#dc2626"
    return f"<span style='color:{color};'>{x:.1f}%</span>"

def get_unit_label(df_source):
    if "unit" not in df_source.columns:
        return ""

    units = (
        df_source["unit"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    units = units[
        (units != "") &
        (units.str.lower() != "nan")
    ]

    unique_units = sorted(units.unique().tolist())

    if len(unique_units) == 1:
        return unique_units[0]

    if len(unique_units) > 1:
        return "mixed unit"

    return ""

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def render_prod_kpi(title, value, wow=None, plan=None, accent="#2563eb"):
    """Renderer KPI Modern"""
    def badge(delta, label):
        if delta is None:
            return ""
        color = "#16a34a" if delta >= 0 else "#dc2626"
        bg = "#f0fdf4" if delta >= 0 else "#fef2f2"
        arrow = "▲" if delta >= 0 else "▼"
        return f"""
        <div style="display:flex; flex-direction:column; align-items:center; background:{bg}; padding:6px 10px; border-radius:8px; border:1px solid #e5e7eb; min-width:80px;">
            <span style="font-size:11px; font-weight:700; color:#6b7280; text-transform:uppercase;">{label}</span>
            <span style="color:{color}; font-size:18px; font-weight:900;">{arrow}{abs(delta):.1f}%</span>
        </div>
        """
    html = f"""
    <div style="border:1px solid #e5e7eb; border-left:6px solid {accent}; border-radius:14px; padding:14px 16px; background:white; box-shadow: 0 4px 12px rgba(0,0,0,0.08); height:120px; display:flex; justify-content:space-between; align-items:center; font-family: 'Inter', sans-serif;">
        <div>
            <div style="font-size:14px; font-weight:800; color:#111827; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.3px;">{title}</div>
            <div style="font-size:32px; font-weight:900; color:#111827;">{value}</div>
        </div>
        <div style="display:flex; gap:10px;">
            {badge(wow, "WoW")}
            {badge(plan, "PLAN")}
        </div>
    </div>
    """
    components.html(html, height=140)

def render_clean_table(df, height=350):
    """Render tabel HTML dengan limit 200 baris untuk performa"""
    df = df.head(200)
    html_table = df.to_html(index=False, border=0, justify="center")
    styled = f"""
    <div id="prod-table-container" style="overflow-x:auto; max-height:{height}px; overflow-y:auto; border-radius:10px; border:1px solid #e5e7eb; margin-bottom: 15px;">
    <style>
    #prod-table-container table {{ border-collapse: collapse; width: 100%; font-size: 14px; font-family: 'Inter', sans-serif; }}
    #prod-table-container th {{ background-color: #1e293b !important; color: white !important; font-weight: 700; text-align: center; padding: 12px 8px; position: sticky; top: 0; z-index: 10; }}
    #prod-table-container td {{ color: #111827; text-align: center; padding: 10px 8px; border-bottom: 1px solid #e2e8f0; }}
    #prod-table-container tr:nth-child(odd) td {{ background-color: #ffffff; font-weight: 600; }}
    #prod-table-container tr:nth-child(even) td {{ background-color: #eef2ff; font-weight: 500; color: #111827; }}
    #prod-table-container tr:hover td {{ background-color: #f1f5f9 !important; }}
    </style>
    {html_table}
    </div>
    """
    components.html(styled, height=height+50, scrolling=True)

# ==========================================
# MAIN PAGE FUNCTION
# ==========================================

def show_productivity_page(df, selected_block, selected_week, selected_category):

    # ======================================
    # INITIAL SETUP & WEEK FILTERING
    # ======================================
    selected_week_ts = pd.to_datetime(selected_week).normalize()
    df_view = df[df["week_date_norm"] == selected_week_ts].copy()

    if selected_category != "All":
        df_view = df_view[df_view["category"] == selected_category]

    if df_view.empty:
        st.warning("Tidak ada data setelah filter untuk minggu ini")
        return

    # ======================================
    # KPI MODE SELECTOR
    # ======================================
    st.markdown("## ⚡ Productivity Dashboard")
    
    kpi_mode = st.radio(
        "Mode KPI",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True,
        key="prod_kpi_mode"
    )

    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range KPI",
            value=(selected_week_ts.date(), selected_week_ts.date()),
            key="prod_custom_range"
        )
    else:
        custom_range = None

    # ======================================
    # LOGIC: DATA KPI SOURCE
    # ======================================
    df_kpi_source = df.copy()
    df_kpi_source["date"] = pd.to_datetime(df_kpi_source["date"], errors="coerce").dt.normalize()

    if selected_category != "All":
        df_kpi_source = df_kpi_source[df_kpi_source["category"] == selected_category]

    kpi_end_date = selected_week_ts

    if kpi_mode == "Weekly":
        df_kpi = df_view.copy()
    elif kpi_mode == "MTD":
        start_month = selected_week_ts.replace(day=1)
        df_kpi = df_kpi_source[(df_kpi_source["date"] >= start_month) & (df_kpi_source["date"] <= kpi_end_date)]
    elif kpi_mode == "YTD":
        start_year = selected_week_ts.replace(month=1, day=1)
        df_kpi = df_kpi_source[(df_kpi_source["date"] >= start_year) & (df_kpi_source["date"] <= kpi_end_date)]
    elif kpi_mode == "Custom" and custom_range and len(custom_range) == 2:
        start = pd.to_datetime(custom_range[0]).normalize()
        end = pd.to_datetime(custom_range[1]).normalize()
        df_kpi = df_kpi_source[(df_kpi_source["date"] >= start) & (df_kpi_source["date"] <= end)]
    else:
        df_kpi = df_view.copy()

    if df_kpi.empty:
        df_kpi = df_view.copy()

    # ======================================
    # KPI PREPARATION (WOW LOGIC)
    # ======================================
    def calc_pct(curr, base):
        if base in [None, 0] or pd.isna(base): return None
        return (curr - base) / base * 100

    # WoW Preparation
    all_weeks_global = sorted(df["week_date_norm"].dropna().unique().tolist())
    prev_week = None
    if selected_week_ts in all_weeks_global:
        idx = all_weeks_global.index(selected_week_ts)
        if idx > 0:
            prev_week = all_weeks_global[idx - 1]

    df_prev = df.copy()
    if prev_week:
        df_prev = df_prev[df_prev["week_date_norm"] == prev_week]
        if selected_category != "All":
            df_prev = df_prev[df_prev["category"] == selected_category]
    else:
        df_prev = pd.DataFrame()

    # ======================================
    # 🔥 KPI PER CATEGORY (MAIN DISPLAY)
    # ======================================
    st.subheader("📊 Key Highlight per Category")

    df_cat_kpi = df_kpi.groupby("category")[["plan", "actual"]].mean().reset_index()
    # Sort descending based on actual performance and limit to 6 for grid stability
    df_cat_kpi = df_cat_kpi.sort_values("actual", ascending=False).head(6)

    if not df_cat_kpi.empty:
        cat_cols = st.columns(len(df_cat_kpi))
        for i, (idx, row) in enumerate(df_cat_kpi.iterrows()):
            cat = row["category"]
            val_plan = row["plan"]
            val_actual = row["actual"]

            delta_plan_cat = calc_pct(val_actual, val_plan)

            # WoW Category Logic
            delta_wow_cat = None
            if kpi_mode == "Weekly" and not df_prev.empty:
                df_prev_cat = df_prev[df_prev["category"] == cat]
                prev_val_cat = df_prev_cat["actual"].mean() if not df_prev_cat.empty else None
                delta_wow_cat = calc_pct(val_actual, prev_val_cat)

            with cat_cols[i]:
                render_prod_kpi(
                    cat,
                    f"{val_actual:.1f}",
                    delta_wow_cat,
                    delta_plan_cat,
                    accent="#6366f1"
                )

    st.write("")
    st.divider()

    # ======================================
    # 📊 BAR CHART BY TYPE
    # ======================================
    st.subheader(
        "📊 Plan vs Actual per Type (All Category)"
        if selected_category == "All"
        else f"📊 Plan vs Actual per Type - {selected_category} (Weekly)"
    )

    df_chart = (
        df_view.groupby("type")[["plan", "actual"]]
        .mean()
        .reset_index()
        .sort_values("actual", ascending=False)
    )

    df_melt = df_chart.melt(
        id_vars="type",
        value_vars=["plan", "actual"],
        var_name="series",
        value_name="value"
    )

    fig_cat = build_fig_cat_cached(df_melt, "type")
    st.plotly_chart(fig_cat, use_container_width=True)
    st.divider()

    # ======================================
    # 📦 WEEKLY SUMMARY - PROFESSIONAL
    # ======================================
    st.subheader("📦 Weekly Summary")
    st.caption("Ringkasan performa unit mingguan yang lebih rapi, compact, dan mudah dibaca.")

    summary_df = df_view.copy()

    weekly_summary = (
        summary_df.groupby(["category", "type", "unit_type", "no_lambung"], as_index=False)
        .agg(
            plan=("plan", "mean"), 
            actual=("actual", "mean"),
            unit=("unit", lambda x: get_unit_label(pd.DataFrame({"unit": x})))
        )
    )

    weekly_summary["variance"] = weekly_summary["actual"] - weekly_summary["plan"]
    weekly_summary["achievement_pct"] = (
        weekly_summary["actual"] / weekly_summary["plan"].replace(0, pd.NA) * 100
    )

    weekly_summary = weekly_summary.sort_values(
        ["category", "type", "achievement_pct"],
        ascending=[True, True, False]
    )

    # --- REVISED DISPLAY SUMMARY COLUMNS WITH UOM ---
    display_summary = pd.DataFrame({
        "Category": weekly_summary["category"].astype(str),
        "Type": weekly_summary["type"].astype(str),
        "Unit Type": weekly_summary["unit_type"].astype(str),
        "Unit": weekly_summary["no_lambung"].astype(str),
        "UoM": weekly_summary["unit"].astype(str),
        "Plan": weekly_summary["plan"].apply(fmt_num),
        "Actual": weekly_summary["actual"].apply(fmt_num),
        "Variance": weekly_summary["variance"].apply(fmt_variance),
        "Achievement": weekly_summary["achievement_pct"].apply(fmt_achievement),
    }).head(200)

    html_table = display_summary.to_html(index=False, escape=False, border=0)

    # --- REVISED CSS (WEEKLY SUMMARY) ---
    components.html(f"""
    <div style="
        overflow:auto;
        max-height:480px;
        border:1px solid #e5e7eb;
        border-radius:14px;
        background:#ffffff;
        box-shadow:0 4px 14px rgba(15,23,42,0.08);
    ">
    <style>
    table {{
        border-collapse:collapse;
        width:100%;
        font-family:{FONT_FAMILY};
        font-size:14px;
    }}
    th {{
        background:#111827;
        color:white;
        padding:13px 14px;
        text-align:center;
        font-weight:700;
        position:sticky;
        top:0;
        z-index:5;
        white-space:nowrap;
    }}
    td {{
        padding:11px 14px;
        text-align:center;
        border-bottom:1px solid #e5e7eb;
        color:#111827;
        font-weight:600;
        white-space:nowrap;
    }}
    tr:nth-child(even) td {{
        background:#f9fafb;
    }}
    tr:hover td {{
        background:#f3f4f6;
    }}
    </style>
    {html_table}
    </div>
    """, height=520, scrolling=True)

    st.divider()

    # ======================================
    # 🏆 TOP UNIT
    # ======================================
    st.subheader("🏆 Top 10 Unit Productivity (Weekly)")

    df_rank = df_view.groupby(["unit_type", "no_lambung"])[["plan", "actual"]].mean().reset_index()
    df_rank["plan"] = df_rank["plan"].round(1)
    df_rank["actual"] = df_rank["actual"].round(1)
    df_rank["achievement"] = ((df_rank["actual"] / df_rank["plan"] * 100).fillna(0).round(1).astype(str) + "%")
    df_rank["unit"] = df_rank["unit_type"].astype(str) + " - " + df_rank["no_lambung"].astype(str)
    df_rank = df_rank.sort_values("actual", ascending=False).head(10)

    render_clean_table(df_rank[["unit", "plan", "actual", "achievement"]], height=300)
    st.divider()

    # ======================================
    # 📈 TREND PRODUCTIVITY
    # ======================================
    st.subheader("📈 Trend Productivity")

    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        trend_period = st.radio("Period", ["Daily", "Weekly"], horizontal=True, key="prod_trend_period")
    with t_col2:
        type_options = ["All"] + sorted(df["type"].dropna().unique().tolist())
        selected_type = st.selectbox("Type", type_options, key="prod_trend_type")
    with t_col3:
        df_unit_source = df.copy()
        if selected_type != "All":
            df_unit_source = df_unit_source[df_unit_source["type"] == selected_type]
        unit_options = ["All"] + sorted((df_unit_source["unit_type"].astype(str) + " - " + df_unit_source["no_lambung"].astype(str)).unique().tolist())
        selected_unit = st.selectbox("Unit", unit_options, key="prod_trend_unit")

    df_trend_source = df.copy() 
    if selected_category != "All":
        df_trend_source = df_trend_source[df_trend_source["category"] == selected_category]

    if selected_type != "All": df_trend_source = df_trend_source[df_trend_source["type"] == selected_type]
    if selected_unit != "All":
        u_parts = selected_unit.split(" - ")
        if len(u_parts) == 2:
            u_type, u_no = u_parts
            df_trend_source = df_trend_source[(df_trend_source["unit_type"] == u_type) & (df_trend_source["no_lambung"] == u_no)]

    selected_range_trend = None
    if trend_period == "Weekly":
        all_weeks_trend = sorted(df_trend_source["week_date_norm"].dropna().unique())
        window_size = 10
        week_windows = []
        for i in range(0, len(all_weeks_trend), window_size):
            chunk = all_weeks_trend[max(0, len(all_weeks_trend)-(i+window_size)): len(all_weeks_trend)-i]
            if chunk:
                label = f"{chunk[0].strftime('%d-%b')} → {chunk[-1].strftime('%d-%b')}"
                week_windows.append({"label": label, "start": chunk[0], "end": chunk[-1]})

        if week_windows:
            selected_range_trend = st.selectbox("Week Range", options=week_windows, format_func=lambda x: x["label"], key="prod_week_range")

    if trend_period == "Daily":
        df_daily = df_trend_source[df_trend_source["week_date_norm"] == selected_week_ts]
        df_trend = df_daily.groupby("date_norm")[["plan", "actual"]].mean().reset_index().sort_values("date_norm")
        x_col = "date_norm"
    else:
        if selected_range_trend:
            df_filtered_week = df_trend_source[(df_trend_source["week_date_norm"] >= selected_range_trend["start"]) & (df_trend_source["week_date_norm"] <= selected_range_trend["end"])]
        else:
            last_weeks = sorted(df_trend_source["week_date_norm"].dropna().unique())[-10:]
            df_filtered_week = df_trend_source[df_trend_source["week_date_norm"].isin(last_weeks)]

        df_trend = df_filtered_week.groupby("week_date_norm")[["plan", "actual"]].mean().reset_index().sort_values("week_date_norm")
        x_col = "week_date_norm"

    if not df_trend.empty:
        df_trend["label"] = df_trend[x_col].dt.strftime("%d-%b")
        if trend_period == "Weekly": df_trend["label"] = df_trend[x_col].dt.strftime("Wk %d-%b")
        df_trend["actual_fmt"] = df_trend["actual"].apply(lambda x: f"{x:.1f}".replace(".", ","))
        df_trend["plan_fmt"] = df_trend["plan"].apply(lambda x: f"{x:.1f}".replace(".", ","))

        fig_trend = build_trend_prod_cached(df_trend, x_col)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Tidak ada data trend untuk pilihan ini.")

    st.divider()

    # ======================================
    # 📊 UNIT PERFORMANCE MONITOR
    # ======================================
    st.subheader("📊 Unit Performance Monitor (Weekly)")

    st.caption(
        "Pilih 1 Category dan 1 Type untuk melihat seluruh unit pada minggu terpilih."
    )

    monitor_category_options = sorted(df_view["category"].dropna().astype(str).unique().tolist())

    if not monitor_category_options:
        st.info("Tidak ada category tersedia untuk Unit Performance Monitor.")
    else:
        m_col1, m_col2 = st.columns(2)

        with m_col1:
            default_category = selected_category if selected_category != "All" else monitor_category_options[0]
            default_category_index = (
                monitor_category_options.index(default_category)
                if default_category in monitor_category_options
                else 0
            )

            monitor_category = st.selectbox(
                "Category",
                options=monitor_category_options,
                index=default_category_index,
                key="prod_unit_monitor_category"
            )

        df_monitor_category = df_view[df_view["category"].astype(str) == str(monitor_category)].copy()

        monitor_type_options = sorted(df_monitor_category["type"].dropna().astype(str).unique().tolist())

        with m_col2:
            if monitor_type_options:
                monitor_type = st.selectbox(
                    "Type",
                    options=monitor_type_options,
                    index=0,
                    key="prod_unit_monitor_type"
                )
            else:
                monitor_type = None

        if not monitor_type:
            st.info("Tidak ada type tersedia untuk category yang dipilih.")
        else:
            df_monitor = df_monitor_category[
                df_monitor_category["type"].astype(str) == str(monitor_type)
            ].copy()

            if df_monitor.empty:
                st.info("Tidak ada data unit untuk kombinasi Category dan Type tersebut.")
            else:
                monitor_unit_label = get_unit_label(df_monitor)
                axis_unit_label = f" ({monitor_unit_label})" if monitor_unit_label else ""

                df_unit_perf = (
                    df_monitor.groupby(["unit_type", "no_lambung"], as_index=False)
                    .agg(
                        plan=("plan", "mean"),
                        actual=("actual", "mean")
                    )
                )

                df_unit_perf["unit"] = (
                    df_unit_perf["unit_type"].astype(str)
                    + " - "
                    + df_unit_perf["no_lambung"].astype(str)
                )

                df_unit_perf["achievement_pct"] = (
                    df_unit_perf["actual"]
                    / df_unit_perf["plan"].replace(0, pd.NA)
                    * 100
                )

                df_unit_perf = df_unit_perf.sort_values("actual", ascending=False)

                df_unit_melt = df_unit_perf.melt(
                    id_vars=["unit", "achievement_pct"],
                    value_vars=["plan", "actual"],
                    var_name="series",
                    value_name="value"
                )

                # --- REVISED COLOR DISCRETE MAP ---
                fig_unit = px.bar(
                    df_unit_melt,
                    x="value",
                    y="unit",
                    color="series",
                    orientation="h",
                    barmode="group",
                    text=df_unit_melt["value"].round(1),
                    template="plotly_white",
                    color_discrete_map={
                        "actual": "#2563eb",
                        "plan": "#f97316"
                    },
                    title=f"Unit Productivity - {monitor_category} / {monitor_type}"
                )

                # --- REVISED GRAPHIC TRACES STYLE ---
                fig_unit.update_traces(
                    textposition="outside",
                    cliponaxis=False,
                    textfont=dict(
                        size=15,
                        color="#000000",
                        family=FONT_FAMILY
                    ),
                    marker=dict(
                        opacity=0.98,
                        line=dict(width=1.2, color="#ffffff")
                    ),
                    hovertemplate="<b>%{y}</b><br>%{fullData.name}: %{x:.1f}<extra></extra>"
                )

                # --- REVISED GRAPHIC LAYOUT STYLE ---
                fig_unit.update_layout(
                    height=max(560, min(3200, 96 * df_unit_perf["unit"].nunique())),
                    margin=dict(l=165, r=140, t=85, b=75),
                    legend_title_text="",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.04,
                        xanchor="right",
                        x=1,
                        font=dict(size=14, color="#000000", family=FONT_FAMILY)
                    ),
                    font=dict(family=FONT_FAMILY, size=15, color="#000000"),
                    plot_bgcolor="#ffffff",
                    paper_bgcolor="#ffffff",
                    bargap=0.52,
                    bargroupgap=0.12,
                    xaxis=dict(
                        title=f"Productivity{axis_unit_label}",
                        tickfont=dict(size=14, color="#000000", family=FONT_FAMILY),
                        title_font=dict(size=16, color="#000000", family=FONT_FAMILY),
                        gridcolor="#e5e7eb",
                        zeroline=False,
                        showline=True,
                        linecolor="#111827",
                        linewidth=1
                    ),
                    yaxis=dict(
                        title="Unit",
                        tickfont=dict(size=16, color="#000000", family=FONT_FAMILY),
                        title_font=dict(size=16, color="#000000", family=FONT_FAMILY),
                        categoryorder="array",
                        categoryarray=df_unit_perf["unit"].tolist()[::-1],
                        showline=False
                    )
                )

                st.plotly_chart(fig_unit, use_container_width=True)

                df_unit_table = df_unit_perf.copy()
                df_unit_table["plan"] = df_unit_table["plan"].round(1)
                df_unit_table["actual"] = df_unit_table["actual"].round(1)
                df_unit_table["achievement_pct"] = df_unit_table["achievement_pct"].round(1)

                df_unit_table["variance"] = df_unit_table["actual"] - df_unit_table["plan"]

                # --- REVISED UNIT PERFORMANCE MONITOR TABLE COLUMNS ---
                display_unit_table = pd.DataFrame({
                    "Unit": df_unit_table["unit"],
                    f"Plan{axis_unit_label}": df_unit_table["plan"].apply(lambda x: fmt_num(x)),
                    f"Actual{axis_unit_label}": df_unit_table["actual"].apply(lambda x: fmt_num(x)),
                    f"Variance{axis_unit_label}": df_unit_table["variance"].apply(lambda x: fmt_variance(x)),
                    "Achievement": df_unit_table["achievement_pct"].apply(fmt_achievement),
                })

                unit_html = display_unit_table.to_html(index=False, escape=False, border=0)

                # --- REVISED CSS (UNIT PERFORMANCE TABLE WITH THE SAME WEEKLY SUMMARY STYLE) ---
                components.html(f"""
                <div style="
                    overflow:auto;
                    max-height:360px;
                    border:1px solid #e5e7eb;
                    border-radius:14px;
                    background:white;
                    box-shadow:0 4px 14px rgba(15,23,42,0.08);
                ">
                <style>
                table {{
                    border-collapse:collapse;
                    width:100%;
                    font-family:{FONT_FAMILY};
                    font-size:14px;
                }}
                th {{
                    background:#111827;
                    color:white;
                    padding:13px 14px;
                    text-align:center;
                    font-weight:700;
                    position:sticky;
                    top:0;
                    z-index:5;
                    white-space:nowrap;
                }}
                td {{
                    padding:11px 14px;
                    text-align:center;
                    border-bottom:1px solid #e5e7eb;
                    color:#111827;
                    font-weight:600;
                    white-space:nowrap;
                }}
                tr:nth-child(even) td {{
                    background:#f9fafb;
                }}
                tr:hover td {{
                    background:#f3f4f6;
                }}
                </style>
                {unit_html}
                </div>
                """, height=400, scrolling=True)

    st.divider()