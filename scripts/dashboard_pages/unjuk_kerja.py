import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# =========================
# 1. METRIC LIST & LABELS
# =========================
UNIT_METRICS = ["pa", "ma", "ua"]

METRIC_LABEL = {
    "pa": "PHYSICAL AVAILABILITY (%)",
    "ma": "MECHANICAL AVAILABILITY (%)",
    "ua": "USE OF AVAILABILITY (%)",
    "hm": "HOUR METER (HOUR)"
}

# =========================
# 2. HELPER & CHART BUILDER
# =========================

def format_number(val, is_float=True):
    if val is None or pd.isna(val):
        return "-"
    if is_float:
        return f"{val:.1f}".replace(".", ",")
    return f"{int(round(val)):,}".replace(",", ".")

def render_clean_table(df, height=350):
    """
    Menggantikan st.dataframe untuk konsistensi UI.
    Header menggunakan desain Dark (#1e293b) dan teks Putih.
    PATCH: Limit data ke 200 rows untuk performa.
    """
    df = df.head(200)
    
    html = df.to_html(index=False, border=0, justify="center")

    styled = f"""
    <div id="unjuk-kerja-table-container" style="overflow-x:auto; max-height:{height}px; overflow-y:auto;
        border-radius:10px; border:1px solid #e5e7eb; margin-bottom: 15px;">
    <style>
    #unjuk-kerja-table-container table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 15px;
        font-family: 'Inter', sans-serif;
    }}
    #unjuk-kerja-table-container th {{
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
    #unjuk-kerja-table-container td {{
        color: #111827;
        font-weight: 500;
        text-align: center;
        vertical-align: middle;
        padding: 10px 8px;
        border-bottom: 1px solid #f1f5f9;
        font-family: 'Inter', sans-serif;
    }}
    #unjuk-kerja-table-container tr:nth-child(even) {{
        background-color: #f9fafb;
    }}
    #unjuk-kerja-table-container tr:hover {{
        background-color: #f1f5f9 !important;
    }}
    </style>
    {html}
    </div>
    """
    st.markdown(styled, unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def build_trend_chart_unit(df_metric, metric_key, metric_label, trend_type):
    """
    Membangun grafik tren berdasarkan tipe (Daily/Weekly).
    """
    if df_metric.empty:
        return None

    df_metric = df_metric.copy()
    df_metric["plan"] = pd.to_numeric(df_metric["plan"], errors="coerce")
    df_metric["actual"] = pd.to_numeric(df_metric["actual"], errors="coerce")

    # PATCH FINAL: Penerapan period eksplisit untuk menghindari rename-risk pattern
    if trend_type == "Daily":
        df_metric = df_metric.copy()
        df_metric["period"] = pd.to_datetime(df_metric["date"]).dt.normalize()

        chart_df = (
            df_metric.groupby("period", as_index=False, observed=True)[["plan", "actual"]]
            .mean()
        )
    else:
        df_metric = df_metric.copy()
        df_metric["period"] = pd.to_datetime(df_metric["week_norm"]).dt.normalize()

        chart_df = (
            df_metric.groupby("period", as_index=False, observed=True)[["plan", "actual"]]
            .mean()
        )

    chart_df = chart_df.sort_values("period")

    if "plan" in chart_df.columns and chart_df["plan"].isna().all():
        chart_df = chart_df.drop(columns=["plan"])

    if chart_df.empty:
        return None

    chart_df["period_label"] = chart_df["period"].dt.strftime("%d-%b")
    if "plan" in chart_df.columns:
        chart_df["plan_fmt"] = chart_df["plan"].apply(lambda x: f"{x:.1f}".replace(".", ",") if pd.notna(x) else "-")
    chart_df["actual_fmt"] = chart_df["actual"].apply(lambda x: f"{x:.1f}".replace(".", ","))

    if "plan" in chart_df.columns:
        y_cols = ["plan", "actual"]
    else:
        y_cols = ["actual"]

    fig = px.line(
        chart_df,
        x="period",
        y=y_cols,
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
        if trace.name == "plan" and "plan_fmt" in chart_df.columns:
            trace.customdata = chart_df[["period_label", "plan_fmt"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Plan : %{customdata[1]}<extra></extra>"
        else:
            trace.customdata = chart_df[["period_label", "actual_fmt"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Actual : %{customdata[1]}<extra></extra>"

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=45, b=40),
        legend_title_text="",
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
        plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=14, color="#000000"),
        title_font=dict(size=16, color="#000000"),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e5e7eb",
            font_size=14,
            font_family="Inter",
            font_color="#000000"
        )
    )

    fig.update_xaxes(
        showgrid=False, 
        tickfont=dict(size=15, color="#000000", family="Inter"),
        tickmode="array",
        tickvals=chart_df["period"],
        ticktext=chart_df["period_label"],
        tickangle=0,
        automargin=True
    )
    
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", tickfont=dict(size=13, color="#000000"))
    return fig

@st.cache_data(show_spinner=False)
def build_snapshot_chart_unit(chart_df, title):
    fig = px.bar(
        chart_df, 
        x="Type", 
        y="Value", 
        color="Type", 
        text="label", 
        title=title, 
        template="plotly_white"
    )
    
    fig.update_traces(
        textposition="outside", 
        textfont=dict(size=16, color="#000000", family="Inter"),
        marker=dict(line=dict(width=0), opacity=0.95)
    )
    
    fig.for_each_trace(
        lambda tr: tr.update(marker_color="#2563eb" if tr.name == "Actual" else "#9ca3af")
    )
    
    fig.update_layout(
        height=240, 
        margin=dict(l=10, r=10, t=40, b=10), 
        showlegend=False, 
        xaxis_title="", 
        yaxis_title="",
        font=dict(family="Inter", size=14, color="#000000"),
        title_font=dict(size=18, color="#000000")
    )

    fig.update_xaxes(
        tickfont=dict(size=16, color="#000000"),
        title_font=dict(size=16, color="#000000")
    )

    fig.update_yaxes(
        tickfont=dict(size=16, color="#000000"),
        title_font=dict(size=16, color="#000000"),
        gridcolor="#e5e7eb"
    )
    return fig

@st.cache_data(show_spinner=False)
def prepare_trend_data(df):
    if df.empty:
        return pd.DataFrame()

    base_cols = ["date", "week_norm", "block", "unit_type", "no_lambung", "type", "category"]
    existing_base = [c for c in base_cols if c in df.columns]

    df_list = []
    
    # Perbaikan logic: Menghindari redundant mapping & performa loop lambat
    metric_pairs = {
        "pa": ["pa_plan", "pa_actual"],
        "ma": ["ma_plan", "ma_actual"],
        "ua": ["ua_plan", "ua_actual"]
    }

    for metric, cols in metric_pairs.items():
        if cols[0] in df.columns and cols[1] in df.columns:
            df_m = df[existing_base + cols].copy()
            df_m["metric"] = metric
            df_m = df_m.rename(columns={cols[0]: "plan", cols[1]: "actual"})
            df_list.append(df_m)

    if "hm" in df.columns:
        df_hm = df[existing_base + ["hm"]].copy()
        df_hm["metric"] = "hm"
        df_hm["plan"] = None
        df_hm = df_hm.rename(columns={"hm": "actual"})
        df_list.append(df_hm)

    if not df_list:
        return pd.DataFrame()

    df_long = pd.concat(df_list, ignore_index=True)
    df_long["unit_full"] = df_long["unit_type"].astype(str) + " - " + df_long["no_lambung"].astype(str)
    
    return df_long

@st.cache_data(show_spinner=False)
def build_perf_table_source(df_current):
    cols = ["date", "unit_type", "no_lambung", 
            "pa_plan", "pa_actual", 
            "ma_plan", "ma_actual", 
            "ua_plan", "ua_actual"]
    
    available_cols = [c for c in cols if c in df_current.columns]
    x = df_current[available_cols]
    df_list = []

    for m in ["pa", "ma", "ua"]:
        plan_col = f"{m}_plan"
        act_col = f"{m}_actual"
        
        if plan_col in x.columns and act_col in x.columns:
            df_p = x[["date", "unit_type", "no_lambung", plan_col]].copy()
            df_p = df_p.rename(columns={plan_col: "Value"})
            df_p["Metric"] = f"{m.upper()} Plan"
            df_list.append(df_p)
            
            df_a = x[["date", "unit_type", "no_lambung", act_col]].copy()
            df_a = df_a.rename(columns={act_col: "Value"})
            df_a["Metric"] = f"{m.upper()} Actual"
            df_list.append(df_a)

    if not df_list:
        return pd.DataFrame()

    df_long = pd.concat(df_list, ignore_index=True)
    df_long["Unit"] = df_long["unit_type"].astype(str) + " - " + df_long["no_lambung"].astype(str)
    return df_long[["Unit", "Metric", "date", "Value"]]

# =========================
# 3. KPI RENDERER
# =========================

def render_unit_kpi(title, value, delta_plan=None, delta_wow=None):
    
    def delta_box(delta, label):
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

    wow_block = delta_box(delta_wow, "WoW")
    plan_block = delta_box(delta_plan, "PLAN")

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
                font-size:34px;
                font-weight:900;
                color:#111827;
            ">
                {value}
            </div>
        </div>

        <div style="display:flex; gap:10px;">
            {wow_block}
            {plan_block}
        </div>
    </div>
    """
    components.html(html, height=140)

# =========================
# MAIN PAGE FUNCTION
# =========================

def show_unjuk_kerja_page(df, selected_block, selected_week, selected_category):
    st.markdown("""
    <style>
    theadr tr th { color: #000000 !important; font-weight: 600 !important; font-size: 14px !important; }
    tbody tr th { color: #000000 !important; font-weight: 600 !important; }
    tbody td { color: #000000 !important; font-weight: 500 !important; }
    </style>
    """, unsafe_allow_html=True)

    df_block = df

    # PATCH: Menggunakan .assign untuk menghindari SettingWithCopyWarning
    if "date_norm" not in df_block.columns or "week_norm" not in df_block.columns:
        df_block = df_block.assign(
            date_norm=pd.to_datetime(df_block["date"], errors="coerce").dt.normalize(),
            week_norm=pd.to_datetime(df_block["week_date"], errors="coerce").dt.normalize()
        )

    st.markdown("### 🚜 Unjuk Kerja")
    st.markdown("---")

    selected_week_ts = pd.to_datetime(selected_week).normalize()

    df_current = df_block[df_block["week_norm"] == selected_week_ts]
    df_filtered = df_current

    if selected_category != "All":
        df_filtered = df_filtered[df_filtered["category"] == selected_category]

    if df_current.empty:
        st.warning(f"Data tidak ditemukan untuk minggu tersebut.")
        return

    # KPI MODE - ONLY FOR KPI CARDS
    kpi_mode = st.radio(
        "Mode KPI",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True,
        key="uk_kpi_mode"
    )

    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range KPI",
            value=(selected_week_ts.date(), selected_week_ts.date()),
            key="uk_custom_range"
        )
    else:
        custom_range = None

    df_kpi_source = df_block

    if kpi_mode == "Weekly":
        df_kpi = df_filtered

    elif kpi_mode == "MTD":
        start_month = selected_week_ts.replace(day=1)
        df_kpi = df_kpi_source[
            (df_kpi_source["date_norm"] >= start_month) &
            (df_kpi_source["date_norm"] <= selected_week_ts)
        ]

    elif kpi_mode == "YTD":
        start_year = selected_week_ts.replace(month=1, day=1)
        df_kpi = df_kpi_source[
            (df_kpi_source["date_norm"] >= start_year) &
            (df_kpi_source["date_norm"] <= selected_week_ts)
        ]

    elif kpi_mode == "Custom" and custom_range and len(custom_range) == 2:
        start = pd.to_datetime(custom_range[0]).normalize()
        end = pd.to_datetime(custom_range[1]).normalize()
        df_kpi = df_kpi_source[
            (df_kpi_source["date_norm"] >= start) &
            (df_kpi_source["date_norm"] <= end)
        ]
    else:
        df_kpi = df_filtered

    if selected_category != "All":
        df_kpi = df_kpi[df_kpi["category"] == selected_category]

    if df_kpi.empty:
        df_kpi = df_filtered

    # KPI CALCULATION
    pa = df_kpi["pa_actual"].mean()
    pa_plan = df_kpi["pa_plan"].mean()
    pa_delta = pa - pa_plan

    ma = df_kpi["ma_actual"].mean()
    ma_plan = df_kpi["ma_plan"].mean()
    ma_delta = ma - ma_plan

    ua = df_kpi["ua_actual"].mean()
    ua_plan = df_kpi["ua_plan"].mean()
    ua_delta = ua - ua_plan

    # WoW CALCULATION
    all_weeks = sorted(df_block["week_norm"].dropna().unique())
    prev_week = None
    if selected_week_ts in all_weeks:
        idx = all_weeks.index(selected_week_ts)
        if idx > 0:
            prev_week = all_weeks[idx - 1]

    df_prev = df_block[df_block["week_norm"] == prev_week] if prev_week else pd.DataFrame()

    if not df_prev.empty and selected_category != "All":
        df_prev_cat = df_prev[df_prev["category"] == selected_category]
        if not df_prev_cat.empty:
            df_prev = df_prev_cat

    def calc_wow(current, prev):
        if prev is None or pd.isna(prev) or prev == 0:
            return None
        return (current - prev) / prev * 100

    if kpi_mode == "Weekly":
        pa_prev = df_prev["pa_actual"].mean() if not df_prev.empty else None
        ma_prev = df_prev["ma_actual"].mean() if not df_prev.empty else None
        ua_prev = df_prev["ua_actual"].mean() if not df_prev.empty else None

        pa_wow = calc_wow(pa, pa_prev)
        ma_wow = calc_wow(ma, ma_prev)
        ua_wow = calc_wow(ua, ua_prev)
    else:
        pa_wow = None
        ma_wow = None
        ua_wow = None

    # 4. KPI CARDS
    st.markdown("## 🚜 Unit Performance Summary")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_unit_kpi("Total Unit", f"{df_current['no_lambung'].nunique()}", None, None)
    with col2:
        render_unit_kpi("Avg PA", f"{format_number(pa)}%", pa_delta, pa_wow)
    with col3:
        render_unit_kpi("Avg MA", f"{format_number(ma)}%", ma_delta, ma_wow)
    with col4:
        render_unit_kpi("Avg UA", f"{format_number(ua)}%", ua_delta, ua_wow)

    st.write("")

    # 5. BAR CHART SUMMARY
    group_col = "type"
    title_text = "Performance by Type (All Category)" if selected_category == "All" else f"Performance by Type (Category: {selected_category})"

    summary = (
        df_filtered.groupby(group_col, observed=True)
        .agg(
            total_unit=("no_lambung", "nunique"),
            avg_pa=("pa_actual", "mean"),
            avg_ma=("ma_actual", "mean"),
            avg_ua=("ua_actual", "mean")
        )
        .reset_index()
        .sort_values("avg_pa", ascending=False)
    )

    chart_df = summary.melt(
        id_vars=group_col,
        value_vars=["avg_pa", "avg_ma", "avg_ua"],
        var_name="metric",
        value_name="value"
    )
    chart_df["metric"] = chart_df["metric"].replace({"avg_pa": "PA", "avg_ma": "MA", "avg_ua": "UA"})

    fig_bar = px.bar(
        chart_df, x=group_col, y="value", color="metric", barmode="group",
        text=chart_df["value"].round(1), title=title_text, template="plotly_white",
        color_discrete_sequence=["#2563eb", "#10b981", "#f59e0b"]
    )
    
    max_val = chart_df["value"].max() if not chart_df.empty else 100
    fig_bar.update_traces(
        textposition="outside", cliponaxis=False,
        textfont=dict(size=14, color="#000000", family="Inter"),
        marker=dict(line=dict(width=0), opacity=0.95),
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1f}<extra></extra>"
    )

    fig_bar.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=55, b=20),
        legend_title_text="",
        xaxis_title="Type",
        yaxis_title="Nilai (%)",
        bargap=0.28,
        font=dict(family="Inter", size=14, color="#000000"),
        xaxis=dict(tickfont=dict(size=14, color="#000000"), title_font=dict(size=15, color="#000000")),
        yaxis=dict(tickfont=dict(size=14, color="#000000"), title_font=dict(size=15, color="#000000"))
    )
    fig_bar.update_yaxes(range=[0, max_val + 10])
    st.plotly_chart(fig_bar, use_container_width=True)

    # 📊 SNAPSHOT BY TYPE
    with st.expander("📊 Snapshot Performance by Type", expanded=False):
        st.caption("Perbandingan Plan vs Actual berdasarkan Type (Berdasarkan blok terpilih).")
        
        col_snap1, col_snap2 = st.columns(2)
        with col_snap1:
            snap_type_options = ["All"] + sorted(df_block["type"].dropna().unique().tolist())
            selected_snap_type = st.selectbox("Filter Type (Snapshot)", snap_type_options, key="snapshot_type_filter")
        with col_snap2:
            snap_metric = st.selectbox("Pilih Metric", ["PA", "MA", "UA", "HM"], key="snapshot_metric")

        df_snap = df_block
        if selected_category != "All":
            df_snap = df_snap[df_snap["category"] == selected_category]
        if selected_snap_type != "All":
            df_snap = df_snap[df_snap["type"] == selected_snap_type]

        if df_snap.empty:
            st.info("Tidak ada data untuk kombinasi filter yang dipilih.")
        else:
            agg_snap = df_snap.groupby("type", observed=True).agg({
                "pa_plan": "mean", "pa_actual": "mean",
                "ma_plan": "mean", "ma_actual": "mean",
                "ua_plan": "mean", "ua_actual": "mean",
                "hm": "mean"
            }).reset_index()

            sort_key = snap_metric.lower() + "_actual" if snap_metric != "HM" else "hm"
            agg_snap = agg_snap.sort_values(sort_key, ascending=False)

            cols_snap = st.columns(3)
            fmt = lambda x: f"{x:.1f}".replace(".", ",")
            
            for i, (idx, row) in enumerate(agg_snap.iterrows()):
                t = row["type"]
                if snap_metric == "PA":
                    p_val, a_val = row["pa_plan"], row["pa_actual"]
                elif snap_metric == "MA":
                    p_val, a_val = row["ma_plan"], row["ma_actual"]
                elif snap_metric == "UA":
                    p_val, a_val = row["ua_plan"], row["ua_actual"]
                else: # HM
                    p_val, a_val = None, row["hm"]

                if snap_metric == "HM":
                    c_df = pd.DataFrame({"Type": ["Actual"], "Value": [a_val]})
                else:
                    c_df = pd.DataFrame({"Type": ["Plan", "Actual"], "Value": [p_val, a_val]})
                
                c_df["label"] = c_df["Value"].apply(fmt)
                fig_s = build_snapshot_chart_unit(c_df, f"{t} - {snap_metric}")
                
                with cols_snap[i % 3]:
                    st.plotly_chart(fig_s, use_container_width=True)

    # 📋 WEEKLY SUMMARY TABLE
    st.markdown("### 📋 Weekly Summary per Unit")
    weekly_summary = (
        df_filtered.groupby(["block", "unit_type", "no_lambung"], observed=True)
        .agg(
            hm_total=("hm", "sum"),
            pa_plan_avg=("pa_plan", "mean"), pa_actual_avg=("pa_actual", "mean"),
            ma_plan_avg=("ma_plan", "mean"), ma_actual_avg=("ma_actual", "mean"),
            ua_plan_avg=("ua_plan", "mean"), ua_actual_avg=("ua_actual", "mean")
        ).reset_index().sort_values("pa_actual_avg", ascending=False)
    )
    
    weekly_summary_fmt = weekly_summary
    for col in weekly_summary_fmt.columns:
        if "avg" in col or "total" in col:
            weekly_summary_fmt[col] = weekly_summary_fmt[col].round(1)

    render_clean_table(weekly_summary_fmt)

    # 🔥 DETAIL TABLE (EXPANDER)
    with st.expander("📊 Tabel Detail (Harian & Performance)", expanded=False):
        col_tab1, col_tab2 = st.columns(2)
        with col_tab1:
            st.markdown("##### Tabel Harian (Hour Meter)")
            pivot_hm = df_current.pivot_table(index=["unit_type", "no_lambung"], columns="date", values="hm", aggfunc="mean", observed=True)
            if not pivot_hm.empty:
                pivot_hm_fmt = pivot_hm.round(2)
                pivot_hm_fmt.columns = pd.to_datetime(pivot_hm_fmt.columns).strftime("%d-%b")
                pivot_hm_fmt = pivot_hm_fmt.reset_index()
                pivot_hm_fmt.columns.name = None 
                render_clean_table(pivot_hm_fmt, height=320)

        with col_tab2:
            st.markdown("##### Performance Unit (PA / MA / UA)")
            df_p_table = build_perf_table_source(df_current)
            if not df_p_table.empty:
                pivot_perf = df_p_table.pivot_table(index=["Unit", "Metric"], columns="date", values="Value", aggfunc="mean", observed=True)
                if not pivot_perf.empty:
                    pivot_perf_fmt = pivot_perf.round(1)
                    pivot_perf_fmt.columns = pd.to_datetime(pivot_perf_fmt.columns).strftime("%d-%b")
                    pivot_perf_fmt = pivot_perf_fmt.reset_index()
                    pivot_perf_fmt.columns.name = None 
                    render_clean_table(pivot_perf_fmt, height=320)

    # 7. TOP & WORST UNIT 
    st.markdown("---")
    
    with st.expander("🏆 Top & Worst Unit", expanded=False):
        st.markdown("### 🏆 Top & Worst Unit")
        rank_mode = st.selectbox("Ranking Based On", ["ALL (PA+MA+UA)", "PA", "MA", "UA", "HM"], key="rank_mode")

        rank_df = df_filtered.groupby(["no_lambung", "unit_type", "category"], as_index=False, observed=True).agg(
            pa_actual=("pa_actual", "mean"), ma_actual=("ma_actual", "mean"),
            ua_actual=("ua_actual", "mean"), hm_total=("hm", "sum")
        )
        
        if rank_mode == "PA": rank_df["score"] = rank_df["pa_actual"]
        elif rank_mode == "MA": rank_df["score"] = rank_df["ma_actual"]
        elif rank_mode == "UA": rank_df["score"] = rank_df["ua_actual"]
        elif rank_mode == "HM": rank_df["score"] = rank_df["hm_total"]
        else: rank_df["score"] = (rank_df["pa_actual"] + rank_df["ma_actual"] + rank_df["ua_actual"]) / 3
        
        top = rank_df.sort_values("score", ascending=False).head(5)
        worst = rank_df.sort_values("score", ascending=True).head(5)

        colA, colB = st.columns(2)
        d_cols = ["no_lambung", "unit_type", "pa_actual", "ma_actual", "ua_actual", "hm_total"]
        with colA:
            st.markdown("🏆 **Top 5**")
            render_clean_table(top[d_cols].round(1))
        with colB:
            st.markdown("⚠️ **Worst 5**")
            render_clean_table(worst[d_cols].round(1))

    # 8. TREND PERFORMANCE
    st.markdown("---")
    st.markdown("## 📈 Trend Performance")
    
    trend_source = df_block
    all_weeks_sorted = sorted(trend_source["week_norm"].dropna().unique().tolist())

    week_windows = []
    w_size = 10
    t_weeks = len(all_weeks_sorted)
    for i in range(0, t_weeks, w_size):
        chunk = all_weeks_sorted[max(0, t_weeks - (i + w_size)): t_weeks - i]
        if not chunk: continue
        label = f"Range: {chunk[0].strftime('%d-%b')} - {chunk[-1].strftime('%d-%b')}"
        week_windows.append({"label": label, "start": chunk[0], "end": chunk[-1]})

    if selected_category != "All":
        df_trend_cat = trend_source[trend_source["category"] == selected_category]
        if not df_trend_cat.empty:
            trend_source = df_trend_cat

    col_t1, col_t2, col_t3, col_t4 = st.columns([1, 1, 2, 2])
    with col_t1: trend_type = st.radio("Period", ["Daily", "Weekly"], horizontal=True, key="u_trend_r")
    with col_t2: 
        t_opts = ["All"] + sorted(trend_source["type"].unique().tolist())
        sel_type = st.selectbox("Type", t_opts, key="u_trend_t")
    
    with col_t4:
        u_opts = ["All"]
        df_u_src = trend_source[trend_source["type"] == sel_type] if sel_type != "All" else trend_source
        u_opts += sorted((df_u_src["unit_type"].astype(str) + " - " + df_u_src["no_lambung"].astype(str)).unique().tolist())
        sel_unit = st.selectbox("Unit Drilldown", u_opts, key="u_trend_u")

    start_w, end_w = None, None
    if trend_type == "Weekly" and week_windows:
        with col_t3:
            sel_win = st.selectbox("Range Minggu", options=week_windows, format_func=lambda x: x["label"], key="u_trend_win")
            start_w, end_w = sel_win["start"], sel_win["end"]

    # Final Drilldown Filters
    if sel_type != "All": 
        trend_source = trend_source[trend_source["type"] == sel_type]
    if sel_unit != "All":
        u_parts = sel_unit.split(" - ")
        if len(u_parts) == 2:
            u_type_s, u_no_s = u_parts
            trend_source = trend_source[(trend_source["unit_type"].astype(str) == u_type_s) & (trend_source["no_lambung"].astype(str) == u_no_s)]
    
    if trend_type == "Weekly" and start_w:
        trend_source = trend_source[(trend_source["week_norm"] >= start_w) & (trend_source["week_norm"] <= end_w)]
    elif trend_type == "Daily":
        trend_source = trend_source[trend_source["week_norm"] == selected_week_ts]

    # FIX REDUNDANT: Memanggil fungsi utama directly tanpa wrapper redundant
    trend_long = prepare_trend_data(trend_source)
    
    if not trend_long.empty:
        m_pairs = [("pa", "ma"), ("ua", "hm")]
        for l_key, r_key in m_pairs:
            cl, cr = st.columns(2)
            for col, m_key in zip([cl, cr], [l_key, r_key]):
                df_m = trend_long[trend_long["metric"] == m_key]
                with col:
                    if not df_m.empty:
                        fig_t = build_trend_chart_unit(df_m, m_key, METRIC_LABEL[m_key], trend_type)
                        if fig_t: st.plotly_chart(fig_t, use_container_width=True)
                    else:
                        st.info(f"No trend data for {m_key.upper()}")
    else:
        st.info("Tidak ada data tren untuk filter yang dipilih.")