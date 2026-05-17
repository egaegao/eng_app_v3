import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# =========================================================
# 🔧 HELPER FORMAT
# =========================================================
def format_number(val, is_float=False):
    if pd.isna(val):
        return "-"
    if is_float:
        return f"{val:.2f}".replace(".", ",")
    return f"{int(round(val)):,}".replace(",", ".")


def format_pct(val):
    if val is None or pd.isna(val):
        return "No data"
    return f"{val:+.1f}%".replace(".", ",")


# =========================================================
# 🎨 KPI RENDERER (FINAL UPDATED DESIGN SYSTEM)
# =========================================================
def render_fleet_kpi(title, value, wow=None, plan=None):
    """Render KPI Card dengan Title Hitam Tegas (Update 14px #111827)"""
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
        border-left:6px solid #3b82f6;
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
                letter-spacing: 0.5px;
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


# =========================================================
# 📊 TREND CHART BUILDER (PATCHED & CACHED)
# =========================================================
@st.cache_data(show_spinner=False)
def build_trend_chart_fleet(df_metric, metric_key, metric_label, trend_type):
    df_metric = df_metric.copy()

    if trend_type == "Daily":
        df_metric["period"] = df_metric["date"].dt.normalize()
        chart_df = (
            df_metric.groupby("period", as_index=False)[["plan", "actual"]]
            .mean()
        )
    else:
        df_metric["period"] = df_metric["week_date"].dt.normalize()
        chart_df = (
            df_metric.groupby("period", as_index=False)[["plan", "actual"]]
            .mean()
        )

    chart_df = chart_df.sort_values("period")

    if chart_df.empty:
        return None

    chart_df["period_label"] = chart_df["period"].dt.strftime("%d-%b")
    chart_df["plan_fmt"] = chart_df["plan"].apply(lambda x: f"{x:.2f}".replace(".", ","))
    chart_df["actual_fmt"] = chart_df["actual"].apply(lambda x: f"{x:.2f}".replace(".", ","))

    fig = px.line(
        chart_df,
        x="period",
        y=["plan", "actual"],
        markers=True,
        title=metric_label,
        template="plotly_white"
    )

    fig.update_traces(mode="lines+markers", line_shape="spline", hoverlabel=dict(namelength=-1))

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
        height=360,
        margin=dict(l=30, r=20, t=40, b=60),
        legend_title_text="",
        xaxis_title="",
        yaxis_title="",
        hovermode="x unified",
        plot_bgcolor="white",
        font=dict(family="Inter, sans-serif", size=14, color="#000000"),
        title_font=dict(size=18, color="#000000")
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=chart_df["period"],
        ticktext=chart_df["period_label"],
        tickangle=0,
        showgrid=False,
        tickfont=dict(size=15, color="#000000")
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#e5e7eb",
        tickfont=dict(size=15, color="#000000")
    )

    return fig


# =========================================================
# 📊 SNAPSHOT CHART BUILDER (PATCHED & CACHED)
# =========================================================
@st.cache_data(show_spinner=False)
def build_snapshot_chart_fleet(chart_df, label):
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
        textfont=dict(size=16, color="black", family="Inter")
    )
    
    fig.for_each_trace(
        lambda t: t.update(marker_color="#2563eb" if t.name == "Actual" else "#9ca3af")
    )
    
    fig.update_layout(
        height=300, 
        showlegend=False, 
        margin=dict(l=30, r=20, t=50, b=40),
        xaxis_title="",
        yaxis_title="Value",
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


# =========================================================
# 🚀 MAIN PAGE
# =========================================================
def show_fleet_page(df, selected_block, selected_week):
    st.markdown("## 🚜 Fleet Performance")

    if df is None or df.empty:
        st.warning("Data fleet tidak tersedia")
        return

    df = df.copy()
    is_plan_actual = "metric" in df.columns

    # Standardisasi Dasar
    df["date"] = pd.to_datetime(df["date"])
    df["week_date"] = pd.to_datetime(df["week_date"], errors="coerce").dt.normalize()
    df["block"] = df["block"].astype(str).str.strip()
    
    df["date_norm"] = df["date"].dt.normalize()
    df["week_date_norm"] = df["week_date"].dt.normalize()

    # =========================
    # VALIDASI DATA (HYBRID)
    # =========================
    if is_plan_actual:
        df["plan"] = pd.to_numeric(df["plan"], errors="coerce")
        df["actual"] = pd.to_numeric(df["actual"], errors="coerce")

        # FILTER DIUBAH DI SINI: Menyaring baris non-kosong dan mengecualikan string "nan" palsu
        df_kpi_val = df[
            df["metric"].notna() &
            (df["metric"].astype(str).str.strip() != "") &
            (df["metric"].astype(str).str.lower().str.strip() != "nan")
        ]
        if not df_kpi_val.empty:
            if df_kpi_val["plan"].isna().any() or df_kpi_val["actual"].isna().any():
                st.error("Ditemukan nilai 'plan' atau 'actual' yang bukan angka pada data Fleet KPI.")
                return

    # Split Data - FILTER DIUBAH DI SINI JUGA: Mengecualikan string "nan" palsu
    df_kpi = df[
        df["metric"].notna() &
        (df["metric"].astype(str).str.strip() != "") &
        (df["metric"].astype(str).str.lower().str.strip() != "nan")
    ].copy()
    df_detail = df[df["loader_id"].notna() & (df["loader_id"].astype(str).str.strip() != "")]

    if not df_kpi.empty:
        df_kpi["metric"] = df_kpi["metric"].astype(str).str.strip()

    # Kolom Required
    required_cols = ["date", "week_date", "block", "metric", "plan", "actual"] if is_plan_actual else \
                    ["date", "week_date", "block", "fleet_type", "loader_type", "loader_id", "hauler_count"]
    
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Kolom tidak lengkap: {missing}")
        return

    # Normalize selected_week_ts agar sinkron
    selected_week_ts = pd.to_datetime(selected_week, errors="coerce").normalize()
    df_week = df[df["week_date_norm"] == selected_week_ts]

    # =========================
    # KPI SECTION
    # =========================
    kpi_mode = st.radio(
        "Pilih Mode KPI",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True,
        key="fleet_kpi_mode"
    )

    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range Tanggal",
            value=(selected_week_ts.date(), selected_week_ts.date()),
            key="fleet_custom_range"
        )
    else:
        custom_range = None

    if is_plan_actual:
        # PREVIOUS WEEK CALCULATION
        all_weeks = sorted(df_kpi["week_date_norm"].dropna().unique())
        prev_week = None
        if selected_week_ts in all_weeks:
            idx = all_weeks.index(selected_week_ts)
            if idx > 0:
                prev_week = all_weeks[idx - 1]

        df_prev = df_kpi[df_kpi["week_date_norm"] == prev_week] if prev_week else pd.DataFrame()

        # Selection Mode Filter
        if kpi_mode == "Weekly":
            kpi_df = df_kpi[df_kpi["week_date_norm"] == selected_week_ts].copy()
        elif kpi_mode == "MTD":
            start_month = selected_week_ts.replace(day=1)
            kpi_df = df_kpi[
                (df_kpi["date_norm"] >= start_month) &
                (df_kpi["date_norm"] <= selected_week_ts)
            ].copy()
        elif kpi_mode == "YTD":
            start_year = selected_week_ts.replace(month=1, day=1)
            kpi_df = df_kpi[
                (df_kpi["date_norm"] >= start_year) &
                (df_kpi["date_norm"] <= selected_week_ts)
            ].copy()
        elif kpi_mode == "Custom" and custom_range and len(custom_range) == 2:
            start = pd.to_datetime(custom_range[0]).normalize()
            end = pd.to_datetime(custom_range[1]).normalize()
            kpi_df = df_kpi[
                (df_kpi["date_norm"] >= start) &
                (df_kpi["date_norm"] <= end)
            ].copy()
        else:
            kpi_df = df_kpi[df_kpi["week_date_norm"] == selected_week_ts].copy()

        if kpi_df.empty:
            kpi_df = df_kpi[df_kpi["week_date_norm"] == selected_week_ts].copy()

        # --- REVISED KPI CALCULATION ENGINE ---
        def calc_kpi_metric(metric_name):
            df_now = kpi_df[kpi_df["metric"] == metric_name]
            
            df_p = pd.DataFrame()
            if not df_prev.empty:
                df_p = df_prev[df_prev["metric"] == metric_name]

            plan = df_now["plan"].mean()
            actual = df_now["actual"].mean()

            wow = None
            if kpi_mode == "Weekly" and not df_p.empty:
                prev_val = df_p["actual"].mean()
                if prev_val and not pd.isna(prev_val) and prev_val != 0:
                    wow = (actual - prev_val) / prev_val * 100

            plan_delta = None
            if plan and not pd.isna(plan) and plan != 0:
                plan_delta = (actual - plan) / plan * 100

            return actual, wow, plan_delta

        kpi_config = [
            ("fleet_ob", "AVG FLEET OB / DAY"),
            ("fleet_cg", "AVG FLEET CG / DAY"),
            ("truck_per_fleet_ob", "AVG TRUCK / FLEET OB"),
            ("truck_per_fleet_cg", "AVG TRUCK / FLEET CG"),
        ]

        st.markdown(f"## 📊 Key Highlight ({kpi_mode})")
        cols_kpi = st.columns(2)
        for i, (metric, label) in enumerate(kpi_config):
            val, wow, plan_d = calc_kpi_metric(metric)
            val_fmt = format_number(val, True)
            with cols_kpi[i % 2]:
                render_fleet_kpi(label, val_fmt, wow, plan_d)
        
        if not kpi_df.empty:
            st.caption(f"📍 KPI Range: {kpi_df['date_norm'].min().strftime('%d %b')} - {kpi_df['date_norm'].max().strftime('%d %b %Y')}")

    else:
        # LEGACY KPI LOGIC
        def calc_delta(now, target):
            if target in [0, None] or pd.isna(target): return None
            return ((now - target) / target) * 100

        all_weeks_legacy = sorted(df["week_date_norm"].dropna().unique().tolist())
        prev_week_legacy = None
        if selected_week_ts in all_weeks_legacy:
            idx = all_weeks_legacy.index(selected_week_ts)
            if idx > 0: prev_week_legacy = all_weeks_legacy[idx - 1]

        df_prev_legacy = df[df["week_date_norm"] == prev_week_legacy] if prev_week_legacy else pd.DataFrame()

        def calc_kpi_legacy(df_source):
            if df_source.empty: return {}, {}
            fleet_daily = df_source.groupby(["date_norm", "fleet_type"])["loader_id"].nunique().reset_index(name="fleet_count")
            avg_fleet = fleet_daily.groupby("fleet_type")["fleet_count"].mean().to_dict()
            truck_avg = df_source.groupby(["fleet_type", "loader_id"])["hauler_count"].mean().reset_index()
            avg_truck = truck_avg.groupby("fleet_type")["hauler_count"].mean().to_dict()
            return avg_fleet, avg_truck

        avg_f_now, avg_t_now = calc_kpi_legacy(df_week)
        avg_f_prev, avg_t_prev = calc_kpi_legacy(df_prev_legacy)

        st.markdown(f"## 📊 Key Highlight ({kpi_mode})")
        cols_kpi = st.columns(2)
        legacy_configs = [
            ("OB Removal", "AVG FLEET OB / DAY", "fleet"),
            ("Coal Getting", "AVG FLEET CG / DAY", "fleet"),
            ("OB Removal", "AVG TRUCK / FLEET OB", "truck"),
            ("Coal Getting", "AVG TRUCK / FLEET CG", "truck"),
        ]
        for i, (key, label, tipe) in enumerate(legacy_configs):
            val_now = avg_f_now.get(key, 0) if tipe == "fleet" else avg_t_now.get(key, 0)
            val_prev = avg_f_prev.get(key, 0) if tipe == "fleet" else avg_t_prev.get(key, 0)
            delta = calc_delta(val_now, val_prev)
            val_fmt = format_number(val_now, True)
            with cols_kpi[i % 2]:
                render_fleet_kpi(label, val_fmt, wow=delta, plan=None)

    # =========================
    # TABLE DAILY SECTION
    # =========================
    st.markdown("## 📊 Tabel Fleet Harian")
    df_detail_week = df_detail[df_detail["week_date_norm"] == selected_week_ts]

    if not df_detail_week.empty:
        df_table = df_detail_week.copy()
        df_table["date_str"] = df_table["date"].dt.strftime("%d-%b")
        all_dates = sorted(df_table["date_str"].unique(), key=lambda x: pd.to_datetime(x, format="%d-%b"))

        pivot_data = {}
        for _, r in df_table.iterrows():
            key = f"{r['fleet_type']} | {r['loader_type']} - {r['loader_id']}"
            date = r["date_str"]
            if key not in pivot_data: pivot_data[key] = {}
            pivot_data[key][date] = int(r["hauler_count"]) if pd.notna(r["hauler_count"]) else None

        for ft in ["OB Removal", "Coal Getting"]:
            df_ft = df_table[df_table["fleet_type"] == ft]
            if not df_ft.empty:
                for date, grp in df_ft.groupby("date_str"):
                    h_key = f"HAULER {ft}"
                    if h_key not in pivot_data: pivot_data[h_key] = {}
                    pivot_data[h_key][date] = int(grp["hauler_count"].sum())
                    l_key = f"LOADER {ft}"
                    if l_key not in pivot_data: pivot_data[l_key] = {}
                    pivot_data[l_key][date] = int(grp["loader_id"].nunique())

        rows = []
        for ft in ["OB Removal", "Coal Getting"]:
            df_ft = df_table[df_table["fleet_type"] == ft]
            if df_ft.empty: continue
            rows.append([f"__{ft.upper()}__"] + [""] * len(all_dates))
            for key, val_dict in pivot_data.items():
                if ft in key and "HAULER" not in key and "LOADER" not in key:
                    row = [key.split("|")[1].strip()]
                    for d in all_dates:
                        val = val_dict.get(d, None)
                        row.append(f"🟢 {val}" if val is not None else "⚪")
                    rows.append(row)
            for k_type in ["HAULER", "LOADER"]:
                k = f"{k_type} {ft}"
                if k in pivot_data:
                    row = [f"{k_type.capitalize()} {ft}"]
                    for d in all_dates: row.append(pivot_data[k].get(d, 0))
                    rows.append(row)
            rows.append([""] * (len(all_dates) + 1))

        table_df = pd.DataFrame(rows, columns=["Unit"] + all_dates).head(200)
        html_table = table_df.to_html(index=False, border=0)
        
        styled_html = f"""
        <div style="overflow-x:auto; max-height:520px; overflow-y:auto; border-radius:10px; border:1px solid #e5e7eb;">
        <style>
            table {{ border-collapse: collapse; width: 100%; font-size: 14px; font-family: 'Inter', sans-serif; }}
            th {{ background-color: #1e293b; color: white; font-weight: 700; text-align: center; padding: 12px 10px; position: sticky; top: 0; z-index: 10; }}
            td {{ text-align: center; padding: 10px; border-bottom: 1px solid #e5e7eb; color: #111827; }}
            tr:nth-child(odd) td {{ background-color: #ffffff; }}
            tr:nth-child(even) td {{ background-color: #f8fafc; }}
            tr:hover td {{ background-color: #e0f2fe; }}
            td:contains("__") {{ background-color: #111827 !important; color: white !important; font-weight: 800; }}
            td:contains("Hauler"), td:contains("Loader") {{ background-color: #dbeafe !important; font-weight: 700; }}
            .dot-green {{ color: #166534; font-weight: bold; background: #dcfce7; border-radius: 4px; padding: 2px 6px; }}
            .dot-gray {{ color: #9ca3af; background: #f3f4f6; border-radius: 4px; padding: 2px 6px; }}
        </style>
        {html_table.replace('🟢', '<span class="dot-green">🟢</span>').replace('⚪', '<span class="dot-gray">⚪</span>')}
        </div>
        """
        components.html(styled_html, height=540, scrolling=True)
    else:
        st.info("Tidak ada data detail fleet untuk minggu ini.")

    # =========================
    # TREND FLEET SECTION
    # =========================
    st.markdown("## 📈 Trend Fleet")
    if is_plan_actual:
        t_type = st.radio("Pilih Trend", ["Daily", "Weekly"], horizontal=True, key="f_trend")
        if t_type == "Weekly":
            all_w = sorted(df_kpi["week_date_norm"].dropna().unique().tolist())
            w_packages = []
            rev_w = list(all_w)[::-1]
            chunks = [rev_w[i:i+10] for i in range(0, len(rev_w), 10)]
            for chunk in chunks:
                c_sort = sorted(chunk)
                lbl = f"{c_sort[0].strftime('%d-%b-%Y')} s/d {c_sort[-1].strftime('%d-%b-%Y')}"
                w_packages.append({"label": lbl, "start": c_sort[0], "end": c_sort[-1]})
            
            sel_pkg = st.selectbox("Pilih Periode Trend", options=w_packages, format_func=lambda x: x["label"])
            df_trend_filtered = df_kpi[(df_kpi["week_date_norm"] >= sel_pkg["start"]) & (df_kpi["week_date_norm"] <= sel_pkg["end"])]
        else:
            df_trend_filtered = df_kpi[df_kpi["week_date_norm"] == selected_week_ts]

        m_list = [("fleet_ob", "Fleet OB"), ("fleet_cg", "Fleet CG"), ("truck_per_fleet_ob", "Truck / Fleet OB"), ("truck_per_fleet_cg", "Truck / Fleet CG")]
        for i in range(0, len(m_list), 2):
            col1, col2 = st.columns(2)
            for col, (mk, ml) in zip([col1, col2], m_list[i:i+2]):
                df_m = df_trend_filtered[df_trend_filtered["metric"] == mk]
                if not df_m.empty:
                    with col:
                        fig = build_trend_chart_fleet(df_m, mk, ml, t_type)
                        if fig: st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Trend detail hanya tersedia untuk data Plan vs Actual")

    # =========================================================
    # 📊 PERFORMANCE SNAPSHOT
    # =========================================================
    st.markdown("## 📊 Performance Snapshot")
    if is_plan_actual:
        df_snap = df_kpi[df_kpi["week_date_norm"] == selected_week_ts].copy()
        snap_configs = [("fleet_ob", "Fleet OB"), ("fleet_cg", "Fleet CG"), ("truck_per_fleet_ob", "Truck / Fleet OB"), ("truck_per_fleet_cg", "Truck / Fleet CG")]
        cols_snap = st.columns(2)
        for i, (m, l) in enumerate(snap_configs):
            df_m = df_snap[df_snap["metric"] == m]
            if df_m.empty: continue
            
            p_val, a_val = df_m["plan"].mean(), df_m["actual"].mean()
            chart_df = pd.DataFrame({"Type": ["Plan", "Actual"], "Value": [p_val, a_val]})
            chart_df["label"] = chart_df["Value"].apply(lambda x: f"{x:.2f}".replace(".", ","))

            fig = build_snapshot_chart_fleet(chart_df, l)
            with cols_snap[i % 2]:
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Snapshot hanya tersedia untuk data Plan vs Actual")