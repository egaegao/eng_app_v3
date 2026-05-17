import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# ==============================
# CONFIG
# ==============================
ROUTE_ORDER = ["Tambang-BJI", "Tambang-SDJ", "BJI-SIG"]

METRIC_GROUP = {
    "coal_hauling": "Coal Hauling (Ton)",
    "dt_running": "DT Running",
    "tr_running": "Trainset Running"
}

# ==============================
# FORMAT NUMBER
# ==============================
def format_number(val, metric):
    if pd.isna(val) or val == "":
        return ""

    if metric == "coal_hauling":
        try:
            return f"{int(float(val)):,}".replace(",", ".")
        except:
            return val
    else:
        try:
            return f"{float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return val

# ==============================
# HELPER
# ==============================
def format_date_header(date_value):
    return pd.to_datetime(date_value).strftime("%d-%b")

# 🔥 PATCH: LIMIT TABLE (OPTIMASI RENDER)
def render_clean_table(df, height=400):
    """Tampilan Table dengan isolasi CSS agar tidak merusak modul lain"""
    # Tambahkan limit 200 row agar browser tidak lag
    df = df.head(200)
    
    html_table = df.to_html(index=False, border=0, justify="center")

    # Menggunakan ID #hauling-table-container untuk isolasi style
    styled = f"""
    <div id="hauling-table-container" style="overflow-x:auto; max-height:{height}px; overflow-y:auto;
        border-radius:10px; border:1px solid #e5e7eb; margin-bottom: 15px;">
    <style>
    #hauling-table-container table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 15px;
        font-family: 'Inter', sans-serif;
    }}
    #hauling-table-container th {{
        background-color: #1e293b !important; /* Header Hitam/Gelap */
        color: #ffffff !important;           /* Teks Putih */
        font-weight: 700;
        text-align: center;
        vertical-align: middle;
        padding: 12px 8px;
        border-bottom: 2px solid #0f172a;
        position: sticky;
        top: 0;
        z-index: 10;
    }}
    #hauling-table-container td {{
        color: #111827;
        font-weight: 500;
        text-align: center;
        vertical-align: middle;
        padding: 10px 8px;
        border-bottom: 1px solid #f1f5f9;
    }}
    #hauling-table-container tr:nth-child(even) {{
        background-color: #f9fafb;
    }}
    #hauling-table-container tr:hover {{
        background-color: #f1f5f9 !important;
    }}
    </style>
    {html_table}
    </div>
    """
    st.markdown(styled, unsafe_allow_html=True)

# ==============================
# 🔧 TREND CHART BUILDER
# ==============================
@st.cache_data(show_spinner=False)
def build_trend_chart_hauling(df_metric, metric_key, metric_label, trend_type):
    """Trend Chart Builder dengan revisi Axis X & Y (Bigger Font)"""
    if metric_key == "coal_hauling":
        agg_func = "sum"
    else:
        agg_func = "mean"

    # --- REVISI BAGIAN AWAL LOGIKA PERIOD & GROUPBY ---
    if trend_type == "Daily":
        df_metric = df_metric.dropna(subset=["date"]).copy()
        df_metric["period"] = df_metric["date"].dt.normalize()

        chart_df = (
            df_metric.groupby("period", as_index=False)
            .agg({"plan": agg_func, "actual": agg_func})
        )
    else:
        df_metric = df_metric.dropna(subset=["week_date"]).copy()
        df_metric["period"] = df_metric["week_date"].dt.normalize()

        chart_df = (
            df_metric.groupby("period", as_index=False)
            .agg({"plan": agg_func, "actual": agg_func})
        )
    # --------------------------------------------------

    chart_df = chart_df.sort_values("period")
    if chart_df.empty:
        return None

    def fmt(val):
        if metric_key == "coal_hauling":
            return f"{int(round(val)):,}".replace(",", ".")
        else:
            return f"{val:.2f}".replace(".", ",")

    chart_df["period_label"] = chart_df["period"].dt.strftime("%d-%b")
    chart_df["plan_fmt"] = chart_df["plan"].apply(fmt)
    chart_df["actual_fmt"] = chart_df["actual"].apply(fmt)

    fig = px.line(
        chart_df,
        x="period",
        y=["plan", "actual"],
        markers=True,
        title=metric_label,
        template="plotly_white"
    )

    fig.update_traces(mode="lines+markers", line_shape="spline")
    fig.for_each_trace(
        lambda t: t.update(
            line=dict(
                width=3 if t.name == "actual" else 2,
                color="#2563eb" if t.name == "actual" else "#9ca3af",
                dash="solid" if t.name == "actual" else "dash"
            ),
            marker=dict(size=8 if t.name == "actual" else 6)
        )
    )

    for trace in fig.data:
        if trace.name == "plan":
            trace.customdata = chart_df[["period_label", "plan_fmt"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Plan : %{customdata[1]}<extra></extra>"
        else:
            trace.customdata = chart_df[["period_label", "actual_fmt"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Actual : %{customdata[1]}<extra></extra>"

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=45, b=65), 
        legend_title_text="",
        xaxis_title="Periode",
        yaxis_title="Nilai",
        hovermode="x unified",
        plot_bgcolor="white",
        font=dict(family="Inter", size=14, color="#000000"),
        title_font=dict(size=16, color="#000000")
    )

    fig.update_xaxes(
        showgrid=False,
        tickfont=dict(size=17, color="#000000", family="Inter"),
        title_font=dict(size=18, color="#000000", family="Inter"),
        tickangle=0,
        automargin=True
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#e5e7eb",
        tickfont=dict(size=16, color="#000000", family="Inter"),
        title_font=dict(size=18, color="#000000", family="Inter")
    )
    
    if trend_type == "Weekly":
        fig.update_xaxes(
            tickmode="array",
            tickvals=chart_df["period"],
            ticktext=chart_df["period"].dt.strftime("%d-%b"),
        )
    return fig

# ==============================
# SNAPSHOT CHART BUILDER
# ==============================
@st.cache_data(show_spinner=False)
def build_snapshot_chart(chart_df, label):
    fig = px.bar(
        chart_df, 
        x="Type", 
        y="Value", 
        color="Type", 
        text="label", 
        title=label, 
        template="plotly_white"
    )
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=15, color="#000000"),
        marker=dict(line=dict(width=0), opacity=0.9),
        hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>"
    )
    fig.for_each_trace(lambda t: t.update(marker_color="#2563eb" if t.name == "Actual" else "#9ca3af"))
    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        xaxis_title="",
        yaxis_title="",
        plot_bgcolor="white",
        bargap=0.35,
        font=dict(family="Inter", size=14, color="#000000")
    )
    fig.update_xaxes(tickfont=dict(size=14, color="#000000"))
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", tickfont=dict(size=14, color="#000000"))
    return fig

# ==============================
# 💎 KPI RENDERER
# ==============================
def render_hauling_kpi(title, value, wow=None, plan=None, accent="#2563eb"):
    def badge(delta, label):
        if delta is None: return ""
        color = "#16a34a" if delta >= 0 else "#dc2626"
        bg = "#f0fdf4" if delta >= 0 else "#fef2f2"
        arrow = "▲" if delta >= 0 else "▼"
        return f"""
        <div style="display:flex; flex-direction:column; align-items:center; background:{bg};
            padding:6px 10px; border-radius:8px; border:1px solid #e5e7eb; min-width:75px;">
            <span style="font-size:11px; font-weight:700; color:#6b7280;">{label}</span>
            <span style="color:{color}; font-size:16px; font-weight:900;">{arrow}{abs(delta):.1f}%</span>
        </div>
        """
    html = f"""
    <div style="border:1px solid #e5e7eb; border-left:6px solid {accent}; border-radius:14px;
        padding:14px 16px; background:white; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        height:115px; display:flex; justify-content:space-between; align-items:center; font-family: 'Inter', sans-serif;">
        <div style="flex: 1;">
            <div style="font-size:14px; font-weight:800; color:#111827; text-transform:uppercase; margin-bottom:4px;">{title}</div>
            <div style="font-size:28px; font-weight:900; color:#111827;">{value}</div>
        </div>
        <div style="display:flex; gap:8px;">
            {badge(wow, "WoW")}
            {badge(plan, "PLAN")}
        </div>
    </div>
    """
    components.html(html, height=135)

# ==============================
# MAIN PAGE
# ==============================
def show_hauling_page(df, selected_block, selected_week):
    st.markdown("## 🚛 Hauling Performance")

    if df is None or df.empty:
        st.warning("Tidak ada data")
        return

    if "route" not in df.columns:
        st.warning("Format file hauling tidak sesuai (kolom 'route' tidak ditemukan)")
        return

    # Normalisasi Data
    df = df.copy()
    df["route"] = df["route"].astype(str).str.strip()
    df["metric"] = df["metric"].astype(str).str.strip()
    df["week_date"] = pd.to_datetime(df["week_date"], errors="coerce").dt.normalize()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.normalize()

    # =========================================================
    # 📊 KEY HIGHLIGHT HAULING (KPI Cards)
    # =========================================================
    master_kpi_df = df[df["metric"].isin(["coal_hauling", "dt_running", "tr_running"])].copy()

    # ===============================
    # 🔥 KPI MODE SELECTOR
    # ===============================
    kpi_mode = st.radio(
        "Pilih Mode KPI",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True,
        key="hauling_kpi_mode"
    )

    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range Tanggal",
            value=(pd.to_datetime(selected_week), pd.to_datetime(selected_week)),
            key="hauling_custom_range"
        )
    else:
        custom_range = None

    if kpi_mode == "Weekly":
        title_kpi = "### 📊 Key Highlight This Week"
    elif kpi_mode == "MTD":
        title_kpi = "### 📊 Key Highlight (MTD)"
    elif kpi_mode == "YTD":
        title_kpi = "### 📊 Key Highlight (YTD)"
    else:
        title_kpi = "### 📊 Key Highlight (Custom)"

    st.markdown(title_kpi)

    all_weeks = sorted(master_kpi_df["week_date"].dropna().unique())
    current_week = pd.to_datetime(selected_week).normalize()

    prev_week = None
    if current_week in all_weeks:
        idx = list(all_weeks).index(current_week)
        if idx > 0:
            prev_week = all_weeks[idx - 1]

    df_prev = master_kpi_df[master_kpi_df["week_date"] == prev_week] if prev_week else pd.DataFrame()

    # ===============================
    # 🔥 KPI DATA SOURCE (FIXED PATCH)
    # ===============================
    master_kpi_df["date"] = pd.to_datetime(
        master_kpi_df["date"],
        errors="coerce"
    ).dt.normalize()

    kpi_end_date = current_week

    if kpi_mode == "Weekly":
        kpi_df = master_kpi_df[master_kpi_df["week_date"] == current_week].copy()

    elif kpi_mode == "MTD":
        start_month = current_week.replace(day=1)
        kpi_df = master_kpi_df[
            (master_kpi_df["date"] >= start_month) &
            (master_kpi_df["date"] <= kpi_end_date)
        ].copy()

    elif kpi_mode == "YTD":
        start_year = current_week.replace(month=1, day=1)
        kpi_df = master_kpi_df[
            (master_kpi_df["date"] >= start_year) &
            (master_kpi_df["date"] <= kpi_end_date)
        ].copy()

    elif kpi_mode == "Custom" and custom_range:
        try:
            start, end = pd.to_datetime(custom_range[0]), pd.to_datetime(custom_range[1])
            start = start.normalize()
            end = end.normalize()
            kpi_df = master_kpi_df[
                (master_kpi_df["date"] >= start) &
                (master_kpi_df["date"] <= end)
            ].copy()
        except:
            kpi_df = master_kpi_df[master_kpi_df["week_date"] == current_week].copy()
    else:
        kpi_df = master_kpi_df[master_kpi_df["week_date"] == current_week].copy()

    # Fallback jika data kosong
    if kpi_df.empty:
        kpi_df = master_kpi_df[master_kpi_df["week_date"] == current_week].copy()

    def calc_kpi(metric, route=None, agg="sum"):
        df_n = kpi_df[kpi_df["metric"] == metric]
        if route and not df_n.empty:
            df_n = df_n[df_n["route"] == route]

        if not df_prev.empty:
            df_p = df_prev[df_prev["metric"] == metric]
            if route:
                df_p = df_p[df_p["route"] == route]
        else:
            df_p = pd.DataFrame()

        if agg == "sum":
            actual_now = df_n["actual"].sum() if not df_n.empty else 0
            plan_now = df_n["plan"].sum() if not df_n.empty else None
            actual_prev = df_p["actual"].sum() if not df_p.empty else None
        else:
            actual_now = df_n["actual"].mean() if not df_n.empty else 0
            plan_now = df_n["plan"].mean() if not df_n.empty else None
            actual_prev = df_p["actual"].mean() if not df_p.empty else None

        # WoW hanya untuk Weekly
        wow = None
        if kpi_mode == "Weekly":
            if actual_prev not in [None, 0] and not pd.isna(actual_prev):
                wow = (actual_now - actual_prev) / actual_prev * 100

        # Plan Achievement
        plan_delta = None
        if plan_now not in [None, 0] and not pd.isna(plan_now):
            plan_delta = (actual_now - plan_now) / plan_now * 100

        return actual_now, wow, plan_delta

    def fmt_int(x): return f"{int(round(x)):,}".replace(",", ".")
    def fmt_float(x): return f"{x:.2f}".replace(".", ",")

    kpis = [
        ("coal_hauling", "Tambang-BJI", "TAMBANG-BJI", "sum", "#3b82f6"),
        ("coal_hauling", "Tambang-SDJ", "TAMBANG-SDJ", "sum", "#10b981"),
        ("coal_hauling", "BJI-SIG", "BJI-SIG", "sum", "#8b5cf6"),
        ("dt_running", "Tambang-BJI", "DT TAMBANG-BJI", "mean", "#f59e0b"),
        ("dt_running", "Tambang-SDJ", "DT TAMBANG-SDJ", "mean", "#ef4444"),
        ("tr_running", "BJI-SIG", "TRAINSET BJI-SIG", "mean", "#6b7280"),
    ]

    cols_kpi = st.columns(3)
    for i, (metric, route, label, agg, color) in enumerate(kpis):
        val, wow, plan = calc_kpi(metric, route, agg)
        val_fmt = fmt_int(val) if agg == "sum" else fmt_float(val)
        with cols_kpi[i % 3]:
            render_hauling_kpi(label, val_fmt, wow, plan, color)
    
    st.caption(f"📍 Mode: {kpi_mode} | Row Count: {len(kpi_df)}")

    # ============================================
    # 📅 TABEL HAULING HARIAN
    # ============================================
    st.markdown("### 📅 Tabel Hauling Harian")
    
    selected_week_ts = pd.to_datetime(selected_week).normalize()
    df_table_filtered = df[
        (df["metric"].isin(METRIC_GROUP.keys())) & 
        (df["week_date"] == selected_week_ts)
    ].copy()

    if not df_table_filtered.empty:
        dates = sorted(df_table_filtered["date"].dt.normalize().dropna().unique())
        rows = []
        for metric_key, metric_label in METRIC_GROUP.items():
            df_metric = df_table_filtered[df_table_filtered["metric"] == metric_key]
            for route in ROUTE_ORDER:
                df_route = df_metric[df_metric["route"] == route]
                if df_route.empty: continue

                row_plan = {"Metric": metric_label, "Route": route, "Type": "Plan", "_metric": metric_key}
                row_actual = {"Metric": "", "Route": "", "Type": "Actual", "_metric": metric_key}

                for d in dates:
                    col_name = format_date_header(d)
                    mask = df_route["date"] == pd.to_datetime(d).normalize()
                    row_plan[col_name] = df_route.loc[mask, "plan"].sum()
                    row_actual[col_name] = df_route.loc[mask, "actual"].sum()
                rows.append(row_plan)
                rows.append(row_actual)

        table_df = pd.DataFrame(rows)
        if not table_df.empty:
            display_df = table_df.copy().astype(object)
            value_cols = [c for c in display_df.columns if c not in ["Metric", "Route", "Type", "_metric"]]
            for i in range(len(display_df)):
                m = display_df.iloc[i]["_metric"]
                for col in value_cols:
                    display_df.at[i, col] = format_number(display_df.at[i, col], m)
            display_df = display_df.drop(columns=["_metric"])
            render_clean_table(display_df, height=520)

    # =========================================================
    # 📈 TREND HAULING
    # =========================================================
    st.markdown("### 📈 Trend Hauling")
    trend_source = df.copy()

    all_weeks_sorted = sorted(trend_source["week_date"].dropna().unique().tolist())
    week_packages = []
    weeks_rev = list(all_weeks_sorted)[::-1] 
    chunks = [weeks_rev[i:i+10] for i in range(0, len(weeks_rev), 10)]

    for chunk in chunks:
        chunk_sorted = sorted(chunk)
        if not chunk_sorted: continue
        start = chunk_sorted[0]
        end = chunk_sorted[-1]
        label = f"{start.strftime('%d-%b-%Y')} s/d {end.strftime('%d-%b-%Y')}"
        week_packages.append({"label": label, "start": start, "end": end})

    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        trend_type = st.radio("Pilih Trend", ["Daily", "Weekly"], horizontal=True, key="hauling_trend_radio")
    
    start_w, end_w = None, None
    if trend_type == "Weekly" and week_packages:
        with col_t2:
            selected_package = st.selectbox(
                "Pilih Periode Trend (10 Minggu)",
                options=week_packages,
                format_func=lambda x: x["label"],
                index=0,
                key="hauling_week_package_select"
            )
            start_w = selected_package["start"]
            end_w = selected_package["end"]

    metric_configs = [
        ("coal_hauling", "Tambang-BJI", "Coal Hauling - Tambang-BJI"),
        ("coal_hauling", "Tambang-SDJ", "Coal Hauling - Tambang-SDJ"),
        ("coal_hauling", "BJI-SIG", "Coal Hauling - BJI-SIG"),
        ("dt_running", "Tambang-BJI", "DT Running - Tambang-BJI"),
        ("dt_running", "Tambang-SDJ", "DT Running - Tambang-SDJ"),
        ("tr_running", "BJI-SIG", "Trainset Running - BJI-SIG"),
    ]

    for i in range(0, len(metric_configs), 2):
        col_c1, col_c2 = st.columns(2)
        for col, cfg in zip([col_c1, col_c2], metric_configs[i:i+2]):
            metric_key, route, label_base = cfg
            df_m = trend_source[(trend_source["metric"] == metric_key) & (trend_source["route"] == route)].copy()

            if trend_type == "Daily" and selected_week:
                df_m = df_m[df_m["week_date"] == selected_week_ts]
            elif trend_type == "Weekly":
                if start_w and end_w:
                    df_m = df_m[(df_m["week_date"] >= start_w) & (df_m["week_date"] <= end_w)]

            if df_m.empty: continue
            unit_label = "Ton" if metric_key == "coal_hauling" else "Unit"
            display_label = f"{label_base} ({unit_label})"

            with col:
                fig = build_trend_chart_hauling(df_m, metric_key, display_label, trend_type)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    # =========================================================
    # 📊 SNAPSHOT HAULING (BAR CHART)
    # =========================================================
    st.markdown("### 📊 Snapshot Hauling (Weekly)")
    df_snap = df[df["week_date"] == selected_week_ts].copy()

    snapshot_configs = [
        ("coal_hauling", "Tambang-BJI", "Tambang-BJI (Ton)"),
        ("coal_hauling", "Tambang-SDJ", "Tambang-SDJ (Ton)"),
        ("coal_hauling", "BJI-SIG", "BJI-SIG (Ton)"),
        ("dt_running", "Tambang-BJI", "DT Tambang-BJI (Unit)"),
        ("dt_running", "Tambang-SDJ", "DT Tambang-SDJ (Unit)"),
        ("tr_running", "BJI-SIG", "Trainset BJI-SIG (Unit)"),
    ]

    cols_snap = st.columns(3)
    for i, (metric, route, label) in enumerate(snapshot_configs):
        df_m = df_snap[(df_snap["metric"] == metric) & (df_snap["route"] == route)]
        if df_m.empty: continue

        if metric == "coal_hauling":
            plan_val = df_m["plan"].sum()
            actual_val = df_m["actual"].sum()
            fmt_snap = lambda x: f"{int(round(x)):,}".replace(",", ".")
        else:
            plan_val = df_m["plan"].mean()
            actual_val = df_m["actual"].mean()
            fmt_snap = lambda x: f"{x:.2f}".replace(".", ",")

        chart_df = pd.DataFrame({"Type": ["Plan", "Actual"], "Value": [plan_val, actual_val]})
        chart_df["label"] = chart_df["Value"].apply(fmt_snap)

        fig = build_snapshot_chart(chart_df, label)
        with cols_snap[i % 3]:
            st.plotly_chart(fig, use_container_width=True)

    st.divider()