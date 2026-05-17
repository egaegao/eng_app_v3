import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# =========================================================
# ⚙️ KONFIGURASI & HELPER
# =========================================================

METRIC_ORDER = [
    "overburden",
    "coal_getting",
    "stripping_ratio",
    "coal_crushing",
    "distance_ob",
    "distance_cg"
]

METRIC_LABEL = {
    "overburden": "OVERBURDEN (BCM)",
    "coal_getting": "COAL GETTING (TON)",
    "stripping_ratio": "STRIPPING RATIO",
    "coal_crushing": "COAL CRUSHING (TON)",
    "distance_ob": "OB DISTANCE (M)",
    "distance_cg": "CG DISTANCE (M)"
}

def format_number(val, metric_key):
    """Helper untuk format angka di tabel (Pemisah ribuan titik)"""
    if pd.isna(val) or val == "":
        return ""

    try:
        val_float = float(val)
        if metric_key in ["overburden", "coal_getting", "coal_crushing"]:
            return f"{round(val_float):,}".replace(",", ".")
        
        # Format decimal dengan koma untuk Indonesia
        return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return val


def format_date_header(date_value):
    return pd.to_datetime(date_value).strftime("%d-%b")


def format_hover_number(val, metric_key):
    """Helper untuk format angka pada hover chart"""
    return format_number(val, metric_key)


# 🔥 PATCH FIX — FUNCTION TABLE (DENGAN LIMIT 200 BARIS)
def render_clean_table(df, height=400):
    """Tampilan Table dengan isolasi CSS agar tidak merusak modul lain"""
    # Batasi data untuk performa rendering
    df_view = df.head(200)
    
    html_table = df_view.to_html(index=False, border=0, justify="center")

    styled = f"""
    <div id="production-table-container" style="overflow-x:auto; max-height:{height}px; overflow-y:auto; 
        border-radius:10px; border:1px solid #e5e7eb; margin-bottom: 15px;">
    <style>
    #production-table-container table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 14px;
        font-family: 'Inter', sans-serif;
    }}
    #production-table-container th {{
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
    #production-table-container td {{
        color: #111827;
        font-weight: 500;
        text-align: center;
        vertical-align: middle;
        padding: 10px 8px;
        border-bottom: 1px solid #f1f5f9;
    }}
    #production-table-container tr:nth-child(even) {{
        background-color: #f9fafb;
    }}
    #production-table-container tr:hover {{
        background-color: #f1f5f9 !important;
    }}
    </style>
    {html_table}
    </div>
    """
    st.markdown(styled, unsafe_allow_html=True)


# =========================================================
# 🏗️ CORE BUILDERS & CACHE AGGREGATION
# =========================================================

@st.cache_data(show_spinner=False)
def build_performance_table(df):
    """PATCH 4A: Cache Performance Table"""
    dates = sorted(df["date"].dropna().dt.normalize().unique().tolist())
    result_rows = []

    for metric_key in METRIC_ORDER:
        df_metric = df[df["metric"] == metric_key]

        if df_metric.empty:
            continue

        row_plan = {
            "Metric": METRIC_LABEL[metric_key],
            "Type": "Plan",
            "_metric_key": metric_key,
        }

        row_actual = {
            "Metric": "",
            "Type": "Actual",
            "_metric_key": metric_key,
        }

        for d in dates:
            day_mask = df_metric["date"].dt.normalize() == pd.to_datetime(d)
            col_name = format_date_header(d)

            row_plan[col_name] = df_metric.loc[day_mask, "plan"].sum()
            row_actual[col_name] = df_metric.loc[day_mask, "actual"].sum()

        result_rows.append(row_plan)
        result_rows.append(row_actual)

    final_df = pd.DataFrame(result_rows)

    if final_df.empty:
        return final_df, final_df

    display_df = final_df.copy().astype(object)
    value_cols = [c for c in display_df.columns if c not in ["Metric", "Type", "_metric_key"]]

    for i in range(len(display_df)):
        m_key = display_df.iloc[i]["_metric_key"]
        for col in value_cols:
            display_df.at[i, col] = format_number(display_df.at[i, col], m_key)

    final_df = final_df.drop(columns=["_metric_key"])
    display_df = display_df.drop(columns=["_metric_key"])

    return final_df, display_df


@st.cache_data(show_spinner=False)
def prepare_trend_data(df_metric, metric_key, trend_type):
    """REVISED: Membatasi kolom sebelum aggregasi untuk efisiensi cache dan perbaikan bug kolom 'period'"""
    # 🔒 pastikan hanya kolom penting (kurangi beban cache)
    df_metric = df_metric[["date", "week_date", "plan", "actual"]].copy()

    if metric_key in ["overburden", "coal_getting", "coal_crushing"]:
        agg_func = "sum"
    else:
        agg_func = "mean"

    if trend_type == "Daily":
        df_metric["period"] = df_metric["date"].dt.normalize()
        chart_df = (
            df_metric.groupby("period", as_index=False)
            .agg({"plan": agg_func, "actual": agg_func})
        )
    else:
        df_metric["period"] = df_metric["week_date"].dt.normalize()
        chart_df = (
            df_metric.groupby("period", as_index=False)
            .agg({"plan": agg_func, "actual": agg_func})
        )

    chart_df = chart_df.sort_values("period")
    return chart_df


@st.cache_data(show_spinner=False)
def build_trend_chart(df_metric, metric_key, metric_label, trend_type):
    """Trend Chart - Rendering logic separated from aggregation"""
    
    # Memanggil data yang sudah di-cache agregasinya
    chart_df = prepare_trend_data(df_metric, metric_key, trend_type)

    if chart_df.empty:
        return None

    chart_df["period_label"] = chart_df["period"].dt.strftime("%d-%b")
    chart_df["plan_hover"] = chart_df["plan"].apply(lambda x: format_hover_number(x, metric_key))
    chart_df["actual_hover"] = chart_df["actual"].apply(lambda x: format_hover_number(x, metric_key))

    fig = px.line(
        chart_df,
        x="period",
        y=["plan", "actual"],
        markers=True,
        title=f"Trend {trend_type} - {metric_label}",
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
            trace.customdata = chart_df[["period_label", "plan_hover"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Plan : %{customdata[1]}<extra></extra>"
        elif trace.name == "actual":
            trace.customdata = chart_df[["period_label", "actual_hover"]].to_numpy()
            trace.hovertemplate = "%{customdata[0]}<br>Actual : %{customdata[1]}<extra></extra>"

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=50, b=60), 
        legend_title_text="",
        xaxis_title="Periode",
        yaxis_title="Nilai",
        hovermode="x unified",
        plot_bgcolor="white",
        font=dict(family="Inter", size=14, color="#000000"),
        title_font=dict(size=16, color="#000000"),
    )
    
    fig.update_xaxes(
        showgrid=False,
        tickfont=dict(size=16, color="#000000", family="Inter"),
        title_font=dict(size=17, color="#000000", family="Inter"),
        tickangle=0,
        automargin=True
    )

    fig.update_yaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor="#f0f0f0",
        tickfont=dict(size=15, color="#000000", family="Inter"),
        title_font=dict(size=17, color="#000000", family="Inter")
    )

    if trend_type == "Weekly":
        fig.update_xaxes(
            tickmode="array",
            tickvals=chart_df["period"],
            ticktext=chart_df["period"].dt.strftime("%d-%b"),
        )

    return fig


@st.cache_data(show_spinner=False)
def prepare_bar_data(df_metric, metric_key):
    """PATCH 4C: Cache Bar Chart Aggregation"""
    if metric_key in ["overburden", "coal_getting", "coal_crushing"]:
        plan_val = df_metric["plan"].sum()
        actual_val = df_metric["actual"].sum()
    else:
        plan_val = df_metric["plan"].mean()
        actual_val = df_metric["actual"].mean()

    return plan_val, actual_val


@st.cache_data(show_spinner=False)
def build_bar_chart(df_metric, metric_key, metric_label):
    """Bar Chart - Rendering logic"""
    
    plan_val, actual_val = prepare_bar_data(df_metric, metric_key)

    chart_df = pd.DataFrame({
        "Type": ["Plan", "Actual"],
        "Value": [plan_val, actual_val]
    })

    chart_df["display_text"] = chart_df["Value"].apply(
        lambda x: format_hover_number(x, metric_key)
    )

    fig = px.bar(
        chart_df,
        x="Type",
        y="Value",
        color="Type",
        text="display_text",
        template="plotly_white",
        title=metric_label
    )

    fig.update_traces(
        textposition="outside",
        textfont=dict(size=15, color="#000000"),
        marker=dict(line=dict(width=0), opacity=0.9),
        hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>"
    )

    fig.for_each_trace(
        lambda t: t.update(
            marker_color="#2563eb" if t.name == "Actual" else "#9ca3af"
        )
    )

    fig.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=35, b=10),
        showlegend=False,
        xaxis_title="",
        yaxis_title="",
        bargap=0.35,
        font=dict(family="Inter", size=14, color="#000000")
    )

    fig.update_xaxes(
        tickfont=dict(size=14, color="#000000"),
        title_font=dict(size=14, color="#000000")
    )

    fig.update_yaxes(
        tickfont=dict(size=14, color="#000000"),
        title_font=dict(size=14, color="#000000"),
        showgrid=True,
        gridcolor="#e5e7eb"
    )

    return fig

# =========================================================
# 🏗️ KPI RENDERER
# =========================================================

def render_prod_kpi(title, value, wow=None, plan=None, accent="#2563eb"):

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
        border-left:6px solid {accent};
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
                white-space: nowrap;
                letter-spacing:0.3px;
            ">
                {title}
            </div>
            <div style="
                font-size:26px;
                font-weight:900;
                color:#111827;
            ">
                {value}
            </div>
        </div>

        <div style="display:flex; gap:8px;">
            {badge(wow, "WoW")}
            {badge(plan, "PLAN")}
        </div>
    </div>
    """
    components.html(html, height=140)

# =========================================================
# 📱 MAIN PAGE FUNCTION
# =========================================================

def show_production_page(df, selected_block, selected_week):
    if df is None or df.empty:
        st.info("Silakan upload file terlebih dahulu.")
        return

    full_df_filtered = df
    
    all_weeks_sorted = sorted(
        full_df_filtered["week_date"].dropna().dt.normalize().unique().tolist()
    )

    selected_week_ts = pd.to_datetime(selected_week, errors="coerce")
    
    if pd.isna(selected_week_ts):
        st.warning("Tanggal minggu terpilih tidak valid.")
        return
        
    selected_week_ts = selected_week_ts.normalize()
    
    current_week_df = full_df_filtered[
        full_df_filtered["week_date"].dt.normalize() == selected_week_ts
    ]

    prev_week = None
    if selected_week_ts in all_weeks_sorted:
        idx = all_weeks_sorted.index(selected_week_ts)
        if idx > 0:
            prev_week = all_weeks_sorted[idx - 1]

    if prev_week:
        prev_df = full_df_filtered[
            full_df_filtered["week_date"].dt.normalize() == prev_week
        ]
    else:
        prev_df = pd.DataFrame()

    # ===============================
    # 🔥 KPI MODE SELECTOR
    # ===============================
    kpi_mode = st.radio(
        "Pilih Mode KPI",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True
    )

    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range Tanggal",
            value=(selected_week_ts, selected_week_ts)
        )
    else:
        custom_range = None

    if kpi_mode == "Weekly":
        title_kpi = "## 📊 Key Highlight This Week"
    elif kpi_mode == "MTD":
        title_kpi = "## 📊 Key Highlight (MTD)"
    elif kpi_mode == "YTD":
        title_kpi = "## 📊 Key Highlight (YTD)"
    else:
        title_kpi = "## 📊 Key Highlight (Custom)"
        
    st.markdown(title_kpi)

    # ===============================
    # 🔥 KPI DATA SOURCE
    # ===============================
    if not pd.api.types.is_datetime64_any_dtype(full_df_filtered["date"]):
        full_df_filtered["date"] = pd.to_datetime(full_df_filtered["date"], errors="coerce")
    
    kpi_end_date = selected_week_ts

    if kpi_mode == "Weekly":
        kpi_df = current_week_df

    elif kpi_mode == "MTD":
        start_month = selected_week_ts.replace(day=1)
        kpi_df = full_df_filtered[
            (full_df_filtered["date"].dt.normalize() >= start_month) &
            (full_df_filtered["date"].dt.normalize() <= kpi_end_date)
        ]

    elif kpi_mode == "YTD":
        start_year = selected_week_ts.replace(month=1, day=1)
        kpi_df = full_df_filtered[
            (full_df_filtered["date"].dt.normalize() >= start_year) &
            (full_df_filtered["date"].dt.normalize() <= kpi_end_date)
        ]

    elif kpi_mode == "Custom" and custom_range:
        try:
            start, end = pd.to_datetime(custom_range[0]), pd.to_datetime(custom_range[1])
            start = start.normalize()
            end = end.normalize()

            kpi_df = full_df_filtered[
                (full_df_filtered["date"].dt.normalize() >= start) &
                (full_df_filtered["date"].dt.normalize() <= end)
            ]
        except:
            kpi_df = current_week_df
    else:
        kpi_df = current_week_df

    if kpi_df.empty:
        kpi_df = current_week_df

    st.caption(f"📍 Mode: {kpi_mode} | Row Count: {len(kpi_df)}")

    # --- 📊 KEY HIGHLIGHTS LOGIC ---
    metric_cache = {
        m: kpi_df[kpi_df["metric"] == m]
        for m in kpi_df["metric"].unique()
    }

    def calc_kpi(metric_key):
        df_now = metric_cache.get(metric_key, pd.DataFrame())
        df_prev = prev_df[prev_df["metric"] == metric_key] if not prev_df.empty else pd.DataFrame()

        if metric_key in ["stripping_ratio", "distance_ob", "distance_cg"]:
            actual_now = df_now["actual"].mean()
            plan_now = df_now["plan"].mean()
        else:
            actual_now = df_now["actual"].sum()
            plan_now = df_now["plan"].sum()

        if kpi_mode != "Weekly" or df_prev.empty:
            wow = None
        else:
            if metric_key in ["stripping_ratio", "distance_ob", "distance_cg"]:
                actual_prev = df_prev["actual"].mean()
            else:
                actual_prev = df_prev["actual"].sum()

            if actual_prev == 0 or pd.isna(actual_prev):
                wow = None
            else:
                wow = (actual_now - actual_prev) / actual_prev * 100

        if plan_now == 0 or pd.isna(plan_now):
            plan_delta = None
        else:
            plan_delta = (actual_now - plan_now) / plan_now * 100

        return actual_now, wow, plan_delta

    kpi_config = [
        ("overburden", "OVERBURDEN (BCM)", "int", "#3b82f6"),
        ("coal_getting", "COAL GETTING (TON)", "int", "#f59e0b"),
        ("stripping_ratio", "STRIPPING RATIO", "float", "#8b5cf6"),
        ("coal_crushing", "COAL CRUSHING (TON)", "int", "#10b981"),
        ("distance_ob", "OB DISTANCE (M)", "int", "#ef4444"),
        ("distance_cg", "CG DISTANCE (M)", "int", "#6b7280"),
    ]

    cols_kpi = st.columns(3)
    for i, (key, label, tipe, color_accent) in enumerate(kpi_config):
        val, wow, plan = calc_kpi(key)
        val_fmt = format_number(val, key)

        with cols_kpi[i % 3]:
            render_prod_kpi(label, val_fmt, wow, plan, color_accent)

    # --- 📊 TABEL PERFORMANCE HARIAN ---
    st.markdown("## 📊 Tabel Performance Harian")
    _, display_df = build_performance_table(current_week_df)

    if not display_df.empty:
        render_clean_table(display_df, height=500)

    # --- 📈 TREND PERIODIK ---
    st.markdown("## 📈 Detail Trend Periodik")

    weeks_rev = list(all_weeks_sorted)[::-1]
    chunks = [weeks_rev[i:i+10] for i in range(0, len(weeks_rev), 10)]

    week_packages = []
    for chunk in chunks:
        chunk_sorted = sorted(chunk)
        label = f"{chunk_sorted[0].strftime('%d-%b-%Y')} s/d {chunk_sorted[-1].strftime('%d-%b-%Y')}"
        week_packages.append({"label": label, "start": chunk_sorted[0], "end": chunk_sorted[-1]})

    start_w, end_w = None, None
    if week_packages:
        selected_package = st.selectbox(
            "Pilih Periode Week untuk Trend Mingguan",
            options=week_packages,
            format_func=lambda x: x["label"]
        )
        start_w, end_w = selected_package["start"], selected_package["end"]
        st.caption(f"📍 Menampilkan data dari {start_w.date()} hingga {end_w.date()}")

    trend_type = st.radio("Pilih Visualisasi Trend", ["Daily", "Weekly"], horizontal=True, key="prod_trend")

    metric_pairs = [("overburden", "coal_getting"), ("stripping_ratio", "coal_crushing"), ("distance_ob", "distance_cg")]

    for left_key, right_key in metric_pairs:
        col1, col2 = st.columns(2)
        for col, metric_key in zip([col1, col2], [left_key, right_key]):
            if trend_type == "Daily":
                df_metric_trend = current_week_df[current_week_df["metric"] == metric_key]
            else:
                df_metric_trend = full_df_filtered[
                    (full_df_filtered["metric"] == metric_key) & 
                    (full_df_filtered["week_date"].dt.normalize() >= start_w) & 
                    (full_df_filtered["week_date"].dt.normalize() <= end_w)
                ]

            if not df_metric_trend.empty:
                with col:
                    fig_trend = build_trend_chart(df_metric_trend, metric_key, METRIC_LABEL[metric_key], trend_type)
                    if fig_trend:
                        st.plotly_chart(fig_trend, use_container_width=True)

    # --- 📊 PERFORMANCE SNAPSHOT ---
    st.markdown("## 📊 Performance Snapshot")
    cols_snap = st.columns(3)
    for i, metric_key in enumerate(METRIC_ORDER):
        df_metric_bar = current_week_df[current_week_df["metric"] == metric_key]
        if not df_metric_bar.empty:
            with cols_snap[i % 3]:
                fig_bar = build_bar_chart(df_metric_bar, metric_key, METRIC_LABEL[metric_key])
                st.plotly_chart(fig_bar, use_container_width=True)