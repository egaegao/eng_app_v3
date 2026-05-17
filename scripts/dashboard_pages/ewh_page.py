import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# ==========================================
# HELPER & CACHE FUNCTIONS
# ==========================================

def format_number(val, is_float=True):
    if val is None or pd.isna(val):
        return "-"
    if is_float:
        return f"{val:.1f}".replace(".", ",")
    return f"{int(round(val)):,}".replace(",", ".")

def format_pct(val):
    if val is None or pd.isna(val):
        return "No data"
    return f"{val:+.1f}%".replace(".", ",")

def render_clean_table(df, height=350):
    """
    Merender DataFrame menggunakan HTML Table 
    dengan header hitam/dark dan font Inter yang seragam.
    Limit 200 rows untuk performa UI.
    """
    df = df.head(200)
    
    html = df.to_html(index=False, border=0, justify="center")

    styled = f"""
    <div id="ewh-table-container" style="overflow-x:auto; max-height:{height}px; overflow-y:auto; border-radius:10px; border:1px solid #e5e7eb; margin-bottom: 15px;">
    <style>
    #ewh-table-container table {{
        border_collapse: collapse;
        width: 100%;
        font-size: 14px;
        font-family: 'Inter', sans-serif;
    }}
    #ewh-table-container th {{
        background-color: #1e293b !important;
        color: #ffffff !important;
        font-weight: 700;
        text-align: center;
        vertical-align: middle;
        padding: 12px 8px;
        border-bottom: 2px solid #0f172a;
        position: sticky;
        top: 0;
        z-index: 10;
    }}
    #ewh-table-container td {{
        color: #111827;
        font-weight: 500;
        text-align: center;
        vertical-align: middle;
        padding: 10px 8px;
        border-bottom: 1px solid #f1f5f9;
        font-family: 'Inter', sans-serif;
    }}
    #ewh-table-container tr:nth-child(even) {{
        background-color: #f9fafb;
    }}
    #ewh-table-container tr:hover {{
        background-color: #f1f5f9 !important;
    }}
    </style>
    {html}
    </div>
    """
    st.markdown(styled, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def filter_ewh_base(df, selected_week, selected_category):
    """Filtering menggunakan normalized columns"""
    selected_week_ts = pd.to_datetime(selected_week).normalize()
    df_current = df[df["week_date_norm"] == selected_week_ts].copy()
    
    if selected_category != "All":
        df_current = df_current[df_current["category"] == selected_category]
        
    return df_current

@st.cache_data(show_spinner=False)
def build_ewh_summary(df_filtered):
    """Cached summary metrics"""
    if df_filtered.empty:
        return 0, 0, 0, 0
    
    avg_plan = df_filtered["ewh_plan"].mean()
    avg_actual = df_filtered["ewh_actual"].mean()
    total_unit = df_filtered["no_lambung"].nunique()

    by_unit = (
        df_filtered.groupby(["unit_type", "no_lambung"], observed=True)
        .agg(ewh_plan=("ewh_plan", "mean"), ewh_actual=("ewh_actual", "mean"))
        .reset_index()
    )
    good_unit = (by_unit["ewh_actual"] >= by_unit["ewh_plan"]).sum() if not by_unit.empty else 0
    
    return avg_plan, avg_actual, total_unit, good_unit

@st.cache_data(show_spinner=False)
def prepare_ewh_trend(df):
    """Pre-aggregate trend data"""
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby(["category", "date"], observed=True)[["ewh_plan", "ewh_actual"]]
        .mean()
        .reset_index()
    )

@st.cache_data(show_spinner=False)
def build_trend_chart_ewh(df_metric, metric_label, trend_type):
    """Trend Chart Builder dengan styling yang konsisten (Biru/Abu)"""
    if df_metric.empty:
        return None

    df_metric = df_metric.copy()
    
    if trend_type == "Daily":
        chart_df = df_metric.rename(columns={"date": "period"})
    else:
        df_metric["week_tmp"] = pd.to_datetime(df_metric["date"]).dt.to_period('W').apply(lambda r: r.start_time)
        chart_df = (
            df_metric.groupby("week_tmp", as_index=False)[["ewh_plan", "ewh_actual"]]
            .mean()
            .rename(columns={"week_tmp": "period"})
        )

    chart_df = chart_df.sort_values("period")
    if chart_df.empty:
        return None

    chart_df["period_label"] = chart_df["period"].dt.strftime("%d-%b")
    chart_df["plan_fmt"] = chart_df["ewh_plan"].apply(lambda x: f"{x:.1f}".replace(".", ",") if pd.notna(x) else "-")
    chart_df["actual_fmt"] = chart_df["ewh_actual"].apply(lambda x: f"{x:.1f}".replace(".", ",") if pd.notna(x) else "-")

    fig = px.line(
        chart_df,
        x="period",
        y=["ewh_plan", "ewh_actual"],
        markers=True,
        title=metric_label,
        template="plotly_white"
    )

    fig.update_traces(mode="lines+markers", line_shape="spline")

    fig.for_each_trace(
        lambda t: t.update(
            line=dict(
                width=3 if t.name == "ewh_actual" else 2,
                color="#2563eb" if t.name == "ewh_actual" else "#9ca3af",
                dash="solid" if t.name == "ewh_actual" else "dash"
            ),
            marker=dict(size=8 if t.name == "ewh_actual" else 6)
        )
    )

    for trace in fig.data:
        if trace.name == "ewh_plan":
            trace.name = "Plan"
            trace.customdata = chart_df[["period_label", "plan_fmt"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Plan : %{customdata[1]} jam<extra></extra>"
        else:
            trace.name = "Actual"
            trace.customdata = chart_df[["period_label", "actual_fmt"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Actual : %{customdata[1]} jam<extra></extra>"

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=45, b=65), 
        legend_title_text="",
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
        plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=14, color="#000000"),
        title_font=dict(size=16, color="#000000"),
        hoverlabel=dict(bgcolor="white", bordercolor="#e5e7eb", font_size=14, font_family="Inter", font_color="#000000")
    )

    fig.update_xaxes(
        showgrid=False,
        tickmode="array",
        tickvals=chart_df["period"],
        ticktext=chart_df["period_label"],
        tickangle=0,
        tickfont=dict(size=17, color="#000000", family="Inter"),
        automargin=True
    )

    fig.update_yaxes(
        showgrid=True, 
        gridcolor="#e5e7eb", 
        tickfont=dict(size=16, color="#000000", family="Inter")
    )

    return fig

# ==========================================
# MODERN KPI RENDERER
# ==========================================

def render_ewh_kpi(title, value, wow=None, plan=None):
    def badge(delta, label):
        if delta is None:
            return ""
        color = "#16a34a" if delta >= 0 else "#dc2626"
        bg = "#f0fdf4" if delta >= 0 else "#fef2f2"
        arrow = "▲" if delta >= 0 else "▼"
        return f"""
        <div style="
            display:flex;
            flex-direction:column;
            align-items:center;
            background:{bg};
            padding:6px 10px;
            border-radius:8px;
            border:1px solid #e5e7eb;
            min-width:70px;
        ">
            <span style="font-size:11px; font-weight:700; color:#6b7280;">
                {label}
            </span>
            <span style="color:{color}; font-size:18px; font-weight:900;">
                {arrow}{abs(delta):.1f}%
            </span>
        </div>
        """
    html = f"""
    <div style="
        border:1px solid #e5e7eb;
        border-left:6px solid #2563eb;
        border-radius:14px;
        padding:14px 16px;
        background:white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        height:120px;
        display:flex;
        justify-content:space-between;
        align-items:center;
        font-family: 'Inter', sans-serif;
    ">
        <div>
            <div style="
                font-size:14px;
                font-weight:800;
                color:#111827;
                text-transform:uppercase;
                margin-bottom:6px;
                letter-spacing:0.3px;
            ">
                {title}
            </div>
            <div style="
                font-size:32px;
                font-weight:900;
                color:#111827;
            ">
                {value}
            </div>
        </div>
        <div style="display:flex; gap:10px;">
            {badge(wow, "WoW")}
            {badge(plan, "PLAN")}
        </div>
    </div>
    """
    components.html(html, height=140)

# ==========================================
# MAIN PAGE FUNCTION
# ==========================================

def show_ewh_page(df, selected_block, selected_week, selected_category):
    st.markdown("""
    <style>
    label, .stRadio label, .stSelectbox label {
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### ⏱️ Effective Working Hour")
    st.markdown("---")

    required_cols = ["date", "week_date", "week_date_norm", "block", "category", "type", "unit_type", "no_lambung", "unit_key", "ewh_plan", "ewh_actual"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning(f"Kolom EWH belum lengkap: {missing}")
        return

    df_block = df.copy()
    df_filtered = filter_ewh_base(df_block, selected_week, selected_category)

    # ===============================
    # KPI MODE (ONLY FOR KPI)
    # ===============================
    kpi_mode = st.radio(
        "Mode KPI",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True,
        key="ewh_kpi_mode"
    )

    selected_week_ts = pd.to_datetime(selected_week).normalize()

    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range KPI",
            value=(selected_week_ts.date(), selected_week_ts.date()),
            key="ewh_custom_range"
        )
    else:
        custom_range = None

    if df_filtered.empty:
        st.warning(f"Data EWH tidak ditemukan untuk Block {selected_block} pada minggu tersebut.")
        return

    # ===============================
    # KPI DATA ONLY (ISOLATED & NORMALIZED)
    # ===============================
    df_kpi_source = df_block.copy()
    
    # FIX 1: Normalize date column to avoid silent drop of end-of-day data
    df_kpi_source["date"] = pd.to_datetime(df_kpi_source["date"], errors="coerce").dt.normalize()

    if kpi_mode == "Weekly":
        df_kpi = df_filtered.copy()
    elif kpi_mode == "MTD":
        start_month = selected_week_ts.replace(day=1)
        df_kpi = df_kpi_source[
            (df_kpi_source["date"] >= start_month) &
            (df_kpi_source["date"] <= selected_week_ts)
        ]
    elif kpi_mode == "YTD":
        start_year = selected_week_ts.replace(month=1, day=1)
        df_kpi = df_kpi_source[
            (df_kpi_source["date"] >= start_year) &
            (df_kpi_source["date"] <= selected_week_ts)
        ]
    elif kpi_mode == "Custom" and custom_range and len(custom_range) == 2:
        # FIX 2: Normalize custom range boundaries
        start = pd.to_datetime(custom_range[0]).normalize()
        end = pd.to_datetime(custom_range[1]).normalize()
        df_kpi = df_kpi_source[
            (df_kpi_source["date"] >= start) &
            (df_kpi_source["date"] <= end)
        ]
    else:
        df_kpi = df_filtered.copy()

    # Category filter untuk KPI
    if selected_category != "All":
        df_kpi = df_kpi[df_kpi["category"] == selected_category]

    # Fallback agar tidak error jika data mode terpilih kosong
    if df_kpi.empty:
        df_kpi = df_filtered.copy()

    # Get weekly context for non-KPI elements and static counts
    _, _, total_unit, good_unit = build_ewh_summary(df_filtered)

    # Override values for KPI cards based on kpi_mode
    avg_plan = df_kpi["ewh_plan"].mean()
    avg_actual = df_kpi["ewh_actual"].mean()

    # --- WoW CALCULATION ---
    all_weeks = sorted(df_block["week_date_norm"].dropna().unique().tolist())
    prev_week = None

    if selected_week_ts in all_weeks:
        idx = all_weeks.index(selected_week_ts)
        if idx > 0:
            prev_week = all_weeks[idx - 1]

    df_prev = df_block[df_block["week_date_norm"] == prev_week].copy() if prev_week else pd.DataFrame()

    if not df_prev.empty and selected_category != "All":
        df_prev_cat = df_prev[df_prev["category"] == selected_category]
        if not df_prev_cat.empty:
            df_prev = df_prev_cat

    avg_prev = df_prev["ewh_actual"].mean() if not df_prev.empty else None

    def calc_pct(curr, base):
        if base in [None, 0] or pd.isna(base):
            return None
        return (curr - base) / base * 100

    # WoW hanya muncul di mode Weekly
    if kpi_mode == "Weekly":
        wow_delta = calc_pct(avg_actual, avg_prev)
    else:
        wow_delta = None

    # FIX 3 & 4: Achievement Logic (Actual / Plan * 100)
    # plan_delta tetap dihitung untuk kebutuhan warna badge pada parameter render_ewh_kpi
    plan_delta = calc_pct(avg_actual, avg_plan)
    achievement = (avg_actual / avg_plan * 100) if avg_plan and avg_plan != 0 else 0

    # UI RENDERING
    st.markdown(f"## ⏱️ EWH Summary ({kpi_mode})")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_ewh_kpi("Total Unit", f"{total_unit}")
    with col2:
        render_ewh_kpi("Avg Plan EWH", f"{format_number(avg_plan)} jam")
    with col3:
        render_ewh_kpi("Avg Actual EWH", f"{format_number(avg_actual)} jam", wow_delta, plan_delta)
    with col4:
        # Menampilkan Achievement sebagai % rasio, bukan delta
        render_ewh_kpi("Achievement", f"{format_number(achievement)}%", wow_delta, plan_delta)

    st.write("")

    st.markdown("## 📊 Performance by Type")
    summary = (
        df_filtered.groupby("type", observed=True)
        .agg(total_unit=("no_lambung", "nunique"), avg_plan=("ewh_plan", "mean"), avg_actual=("ewh_actual", "mean"))
        .reset_index()
        .sort_values("avg_actual", ascending=False)
    )

    if not summary.empty:
        chart_df = summary.melt(id_vars="type", value_vars=["avg_plan", "avg_actual"], var_name="metric", value_name="value")
        chart_df["metric"] = chart_df["metric"].replace({"avg_plan": "Plan", "avg_actual": "Actual"})

        fig_bar = px.bar(
            chart_df, x="type", y="value", color="metric", barmode="group",
            text=chart_df["value"].round(1), title="Average EWH by Type (Weekly)",
            template="plotly_white", color_discrete_sequence=["#9ca3af", "#2563eb"]
        )
        
        fig_bar.update_traces(
            textposition="outside", 
            cliponaxis=False, 
            textfont=dict(size=14, color="#000000"), 
            marker=dict(opacity=0.95)
        )
        
        fig_bar.update_layout(
            height=360, 
            margin=dict(l=20, r=20, t=55, b=20), 
            legend_title_text="", 
            bargap=0.28,
            font=dict(family="Inter", size=14, color="#000000"),
            xaxis=dict(tickfont=dict(size=14, color="#000000"), title_font=dict(size=15, color="#000000")),
            yaxis=dict(tickfont=dict(size=14, color="#000000"), title_font=dict(size=15, color="#000000"))
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### 📋 Weekly Summary per Unit")
    weekly_summary = (
        df_filtered.groupby(["block", "category", "unit_type", "no_lambung"], observed=True)
        .agg(ewh_plan_avg=("ewh_plan", "mean"), ewh_actual_avg=("ewh_actual", "mean"))
        .reset_index()
    )
    # Gunakan small epsilon untuk menghindari division by zero
    weekly_summary["achievement_pct"] = (weekly_summary["ewh_actual_avg"] / weekly_summary["ewh_plan_avg"].replace(0, 0.001) * 100)

    weekly_summary_fmt = weekly_summary.copy()
    weekly_summary_fmt["ewh_plan_avg"] = weekly_summary_fmt["ewh_plan_avg"].round(1)
    weekly_summary_fmt["ewh_actual_avg"] = weekly_summary_fmt["ewh_actual_avg"].round(1)
    weekly_summary_fmt["achievement_pct"] = weekly_summary_fmt["achievement_pct"].round(1)
    
    render_clean_table(weekly_summary_fmt)

    with st.expander("📊 Tabel Detail Harian EWH", expanded=False):
        pivot_plan = df_filtered.pivot_table(index=["category", "unit_type", "no_lambung"], columns="date", values="ewh_plan", aggfunc="mean", observed=True)
        pivot_actual = df_filtered.pivot_table(index=["category", "unit_type", "no_lambung"], columns="date", values="ewh_actual", aggfunc="mean", observed=True)

        col_tab1, col_tab2 = st.columns(2)
        with col_tab1:
            st.markdown("##### Tabel Harian EWH Plan")
            if not pivot_plan.empty:
                pivot_plan_fmt = pivot_plan.copy().round(1)
                pivot_plan_fmt.columns = [pd.to_datetime(c).strftime("%d-%b") for c in pivot_plan_fmt.columns]
                pivot_plan_fmt = pivot_plan_fmt.reset_index()
                render_clean_table(pivot_plan_fmt, height=320)
        
        with col_tab2:
            st.markdown("##### Tabel Harian EWH Actual")
            if not pivot_actual.empty:
                pivot_actual_fmt = pivot_actual.copy().round(1)
                pivot_actual_fmt.columns = [pd.to_datetime(c).strftime("%d-%b") for c in pivot_actual_fmt.columns]
                pivot_actual_fmt = pivot_actual_fmt.reset_index()
                render_clean_table(pivot_actual_fmt, height=320)

    st.markdown("---")
    
    # ==========================================
    # IMPLEMENTASI LAZY RENDER: TOP & WORST UNIT
    # ==========================================
    with st.expander("🏆 Top & Worst Unit", expanded=False):
        st.markdown("### 🏆 Top & Worst Unit")
        rank_mode = st.selectbox("Ranking Based On", ["Actual EWH", "Achievement vs Plan"], key="ewh_rank_mode")

        rank_df = (
            df_filtered.groupby(["no_lambung", "unit_type", "category"], as_index=False, observed=True)
            .agg(ewh_plan=("ewh_plan", "mean"), ewh_actual=("ewh_actual", "mean"))
        )
        rank_df["achievement_pct"] = (rank_df["ewh_actual"] / rank_df["ewh_plan"].replace(0, 0.001)) * 100
        rank_df["score"] = rank_df["ewh_actual"] if rank_mode == "Actual EWH" else rank_df["achievement_pct"]

        top = rank_df.sort_values("score", ascending=False).head(5)
        worst = rank_df.sort_values("score", ascending=True).head(5)

        colA, colB = st.columns(2)
        d_cols = ["no_lambung", "unit_type", "category", "ewh_plan", "ewh_actual", "achievement_pct"]

        with colA:
            st.markdown("🏆 **Top 5**")
            render_clean_table(top[d_cols].round(1))
        with colB:
            st.markdown("⚠️ **Worst 5**")
            render_clean_table(worst[d_cols].round(1))

    st.markdown("---")
    
    # ==========================================
    # IMPLEMENTASI LAZY RENDER: TREND EWH BLOCK
    # ==========================================
    with st.expander("📈 Trend EWH", expanded=False):
        st.markdown("## 📈 Trend EWH")
        trend_source = df_block.copy()
        
        if selected_category != "All":
            df_trend_cat = trend_source[
                trend_source["category"].astype(str).str.strip() == str(selected_category).strip()
            ]
            if not df_trend_cat.empty:
                trend_source = df_trend_cat

        col_t1, col_t2, col_t3, col_t4 = st.columns([1, 1, 2, 2])
        with col_t1:
            trend_type = st.radio("Period", ["Daily", "Weekly"], horizontal=True, key="ewh_trend_r")
        with col_t2:
            t_opts = ["All"] + sorted(trend_source["type"].dropna().unique().tolist())
            sel_type = st.selectbox("Type", t_opts, key="ewh_trend_t")
        with col_t4:
            df_u_src = trend_source[trend_source["type"] == sel_type] if sel_type != "All" else trend_source
            u_opts = ["All"] + sorted(df_u_src["unit_key"].unique().tolist())
            sel_unit = st.selectbox("Unit Drilldown", u_opts, key="ewh_trend_u")

        if sel_type != "All":
            trend_source = trend_source[trend_source["type"] == sel_type]
        if sel_unit != "All":
            trend_source = trend_source[trend_source["unit_key"] == sel_unit]

        if trend_type == "Weekly":
            all_weeks_trend = sorted(trend_source["week_date_norm"].dropna().unique().tolist())
            week_windows = []
            w_size = 10
            for i in range(0, len(all_weeks_trend), w_size):
                chunk = all_weeks_trend[max(0, len(all_weeks_trend) - (i + w_size)): len(all_weeks_trend) - i]
                if chunk:
                    label = f"Range: {chunk[0].strftime('%d-%b')} - {chunk[-1].strftime('%d-%b')}"
                    week_windows.append({"label": label, "start": chunk[0], "end": chunk[-1]})
            
            if week_windows:
                with col_t3:
                    sel_win = st.selectbox("Range Minggu", options=week_windows, format_func=lambda x: x["label"], key="ewh_trend_win")
                    trend_source = trend_source[(trend_source["week_date_norm"] >= sel_win["start"]) & (trend_source["week_date_norm"] <= sel_win["end"])]
        else:
            trend_source = trend_source[trend_source["week_date_norm"] == selected_week_ts]

        trend_final = prepare_ewh_trend(trend_source)
        if trend_final.empty:
            st.info("No trend data available for current filter.")
        else:
            available_categories = sorted(trend_final["category"].unique().tolist())
            preferred_order = ["OB Removal", "Coal Getting", "Coal Hauling"]
            ordered_categories = [c for c in preferred_order if c in available_categories] + [c for c in available_categories if c not in preferred_order]

            for i in range(0, len(ordered_categories), 2):
                col_l, col_r = st.columns(2)
                for idx, col in [(i, col_l), (i+1, col_r)]:
                    if idx < len(ordered_categories):
                        cat = ordered_categories[idx]
                        df_cat = trend_final[trend_final["category"] == cat]
                        with col:
                            fig = build_trend_chart_ewh(df_cat, f"EWH - {cat}", trend_type)
                            if fig: 
                                st.plotly_chart(fig, use_container_width=True)
                            else: 
                                st.info(f"No data for {cat}")