import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

# ==============================
# CONFIG & HELPERS
# ==============================

CATEGORY_ORDER = [
    "OB Removal",
    "Coal Getting",
    "Road Maintenance",
    "Dewatering & Pit Service",
    "CCP",
    "Coal Hauling",
    "Mining Aux",
]

METRIC_LABEL = {
    "fuel": "Fuel (Liter)",
    "fuel_ratio": "Fuel Ratio",
}


def format_number(val, decimal=0):
    if val is None or pd.isna(val):
        return "-"

    try:
        val = float(val)
    except Exception:
        return str(val)

    if decimal == 0:
        return f"{int(round(val)):,}".replace(",", ".")

    return f"{val:,.{decimal}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_chart_text(val, decimal=0):
    return format_number(val, decimal)


def get_metric_decimal(metric):
    # PATCH: Diubah menjadi 3 desimal untuk fuel_ratio agar perbedaan MTD/YTD terlihat
    return 3 if metric == "fuel_ratio" else 0


def get_metric_agg(metric):
    return "mean" if metric == "fuel_ratio" else "sum"


def metric_unit_label(metric):
    return "Ratio" if metric == "fuel_ratio" else "Liter"


def render_kpi_card(title, actual_val, delta_wow=None, delta_plan=None):
    def get_delta_html(delta, label_prefix=""):
        if delta is None:
            return ""

        # Untuk Fuel Ratio: naik = merah karena makin boros (overconsumption)
        color = "#dc2626" if delta >= 0 else "#16a34a"
        bg_color = "#fef2f2" if delta >= 0 else "#f0fdf4"
        symbol = "▲" if delta >= 0 else "▼"

        return f"""
            <div style="
                display:flex;
                flex-direction:column;
                align-items:center;
                background-color:{bg_color};
                padding:6px 10px;
                border-radius:8px;
                min-width:80px;
                border:1px solid #e5e7eb;
            ">
                <span style="font-size:11px; color:#6b7280; font-weight:700; text-transform:uppercase;">
                    {label_prefix}
                </span>
                <span style="color:{color}; font-weight:900; font-size:18px;">
                    {symbol}{abs(delta):.1f}%
                </span>
            </div>
        """

    wow_html = get_delta_html(delta_wow, "WoW")
    plan_html = get_delta_html(delta_plan, "PLAN")

    card_html = f"""
    <div style="
        border:1px solid #e5e7eb;
        border-left:6px solid #2563eb;
        border-radius:14px;
        padding:14px 16px;
        background:white;
        font-family:'Inter', sans-serif;
        box-shadow:0 4px 12px rgba(0,0,0,0.08);
        height:120px;
        display:flex;
        justify-content:space-between;
        align-items:center;
    ">
        <div>
            <div style="
                font-size:15px;
                font-weight:800;
                color:#111827;
                text-transform:uppercase;
                margin-bottom:4px;
            ">
                {title}
            </div>
            <div style="font-size:32px; font-weight:900; color:#111827;">
                {actual_val}
            </div>
        </div>
        <div style="display:flex; gap:10px;">
            {wow_html}
            {plan_html}
        </div>
    </div>
    """
    components.html(card_html, height=140)


def render_clean_table(df, height=500):
    df = df.head(200)
    html_table = df.to_html(index=False, border=0, justify="center")

    styled = f"""
    <div id="fuel-table-container" style="
        overflow-x:auto;
        max-height:{height}px;
        overflow-y:auto;
        border-radius:10px;
        border:1px solid #e5e7eb;
        margin-bottom:15px;
    ">
    <style>
    #fuel-table-container table {{
        border-collapse:collapse;
        width:100%;
        font-size:14px;
        font-family:'Inter', sans-serif;
    }}
    #fuel-table-container th {{
        background-color:#1e293b !important;
        color:#ffffff !important;
        font-weight:700;
        text-align:center;
        padding:12px 8px;
        position:sticky;
        top:0;
        z-index:10;
    }}
    #fuel-table-container td {{
        color:#111827;
        font-weight:500;
        text-align:center;
        padding:10px 8px;
        border-bottom:1px solid #e2e8f0;
        white-space: nowrap;
    }}
    #fuel-table-container tr:nth-child(odd) td {{
        background-color:#ffffff;
    }}
    #fuel-table-container tr:nth-child(even) td {{
        background-color:#f8fafc;
    }}
    #fuel-table-container tr:hover td {{
        background-color:#f1f5f9 !important;
    }}
    </style>
    {html_table}
    </div>
    """
    st.markdown(styled, unsafe_allow_html=True)


def build_daily_detail_table(df_metric, metric):
    decimal = get_metric_decimal(metric)
    agg = get_metric_agg(metric)

    dates = sorted(df_metric["date"].dt.normalize().dropna().unique())
    rows = []

    categories = [c for c in CATEGORY_ORDER if c in df_metric["category"].dropna().unique().tolist()]
    categories += sorted([c for c in df_metric["category"].dropna().unique().tolist() if c not in categories])

    for cat in categories:
        df_cat = df_metric[df_metric["category"] == cat]

        row_actual = {"Category": cat, "Type": "Actual"}
        row_plan = {"Category": "", "Type": "Plan"}

        for d in dates:
            day_data = df_cat[df_cat["date"].dt.normalize() == d]
            col_name = pd.to_datetime(d).strftime("%d-%b")

            if agg == "sum":
                actual_val = day_data["actual"].sum()
                plan_val = day_data["plan"].sum()
            else:
                actual_val = day_data["actual"].mean()
                plan_val = day_data["plan"].mean()

            row_actual[col_name] = format_number(actual_val, decimal)
            row_plan[col_name] = format_number(plan_val, decimal)

        rows.append(row_actual)
        rows.append(row_plan)

    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def build_category_bar_chart(df_metric, metric, title):
    decimal = get_metric_decimal(metric)
    agg = get_metric_agg(metric)

    if agg == "sum":
        chart_df = (
            df_metric.groupby("category", observed=True)[["actual", "plan"]]
            .sum()
            .reset_index()
        )
    else:
        chart_df = (
            df_metric.groupby("category", observed=True)[["actual", "plan"]]
            .mean()
            .reset_index()
        )

    chart_df["category"] = pd.Categorical(
        chart_df["category"],
        categories=CATEGORY_ORDER,
        ordered=True,
    )
    chart_df = chart_df.sort_values("category")
    chart_df["actual_label"] = chart_df["actual"].apply(lambda x: format_chart_text(x, decimal))
    chart_df["plan_label"] = chart_df["plan"].apply(lambda x: format_chart_text(x, decimal))

    melt_df = chart_df.melt(
        id_vars=["category", "actual_label", "plan_label"],
        value_vars=["actual", "plan"],
        var_name="Type",
        value_name="Value",
    )

    melt_df["Type"] = melt_df["Type"].replace({"actual": "Actual", "plan": "Plan"})
    melt_df["Label"] = melt_df.apply(
        lambda r: format_chart_text(r["Value"], decimal),
        axis=1,
    )

    fig = px.bar(
        melt_df,
        x="category",
        y="Value",
        color="Type",
        barmode="group",
        text="Label",
        title=title,
        template="plotly_white",
        color_discrete_map={"Actual": "#2563eb", "Plan": "#94a3b8"},
    )

    fig.update_traces(
        textposition="outside",
        textfont=dict(size=15, color="#000000", family="Inter"),
        marker=dict(opacity=0.95),
        hovertemplate="<b>%{fullData.name}</b><br>%{y}<extra></extra>",
    )

    y_max = melt_df["Value"].max()
    y_max = y_max * 1.25 if pd.notna(y_max) and y_max > 0 else 1

    fig.update_layout(
        height=430,
        margin=dict(l=50, r=20, t=60, b=100),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=15, color="#000000", family="Inter"),
            itemwidth=80,
            itemsizing="constant"
        ),
        legend_title_text="",
        font=dict(family="Inter", size=14, color="#000000"),
        title=dict(font=dict(size=20, color="#000000")),
        bargap=0.28,
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e5e7eb",
            font_size=14,
            font_family="Inter",
            font_color="#000000",
        ),
        yaxis=dict(range=[0, y_max]),
    )

    fig.update_xaxes(
        title_text="Category",
        tickfont=dict(size=14, color="#000000", family="Inter"),
        title_font=dict(size=16, color="#000000", family="Inter"),
        tickangle=0,
        showgrid=False,
    )

    fig.update_yaxes(
        title_text=metric_unit_label(metric),
        tickfont=dict(size=14, color="#000000", family="Inter"),
        title_font=dict(size=16, color="#000000", family="Inter"),
        showgrid=True,
        gridcolor="#e5e7eb",
    )

    return fig


@st.cache_data(show_spinner=False)
def build_trend_chart(df_source, metric, trend_option, current_week, selected_range, category_filter):
    decimal = get_metric_decimal(metric)
    agg = get_metric_agg(metric)
    label = METRIC_LABEL[metric]

    df_metric = df_source[df_source["metric"] == metric].copy()
    df_metric["week_date"] = pd.to_datetime(df_metric["week_date"]).dt.normalize()
    current_week = pd.to_datetime(current_week).normalize()

    if category_filter != "All":
        df_cat = df_metric[df_metric["category"] == category_filter]
        if not df_cat.empty:
            df_metric = df_cat

    if df_metric.empty:
        return None

    # --- IMPLEMENTASI PATCH FINAL (ANTI RENAME RISK) ---
    if trend_option == "Daily":
        chart_data = df_metric[df_metric["week_date"] == current_week].copy()

        if chart_data.empty:
            return None

        chart_data["period"] = chart_data["date"].dt.normalize()

        if agg == "sum":
            chart_df = (
                chart_data.groupby("period", as_index=False)
                .agg({"actual": "sum", "plan": "sum"})
            )
        else:
            chart_df = (
                chart_data.groupby("period", as_index=False)
                .agg({"actual": "mean", "plan": "mean"})
            )

    else:
        if selected_range:
            start_r = pd.to_datetime(selected_range["start"]).normalize()
            end_r = pd.to_datetime(selected_range["end"]).normalize()

            chart_data = df_metric[
                (df_metric["week_date"] >= start_r)
                & (df_metric["week_date"] <= end_r)
            ].copy()
        else:
            chart_data = df_metric.copy()

        if chart_data.empty:
            return None

        chart_data["period"] = chart_data["week_date"].dt.normalize()

        if agg == "sum":
            chart_df = (
                chart_data.groupby("period", as_index=False)
                .agg({"actual": "sum", "plan": "sum"})
            )
        else:
            chart_df = (
                chart_data.groupby("period", as_index=False)
                .agg({"actual": "mean", "plan": "mean"})
            )
    # --- END OF PATCH ---

    chart_df = chart_df.sort_values("period")
    chart_df["label"] = chart_df["period"].dt.strftime("%d-%b")
    chart_df["actual_fmt"] = chart_df["actual"].apply(lambda x: format_chart_text(x, decimal))
    chart_df["plan_fmt"] = chart_df["plan"].apply(lambda x: format_chart_text(x, decimal))

    fig = px.line(
        chart_df,
        x="period",
        y=["actual", "plan"],
        title=f"Trend {label}",
        markers=True,
        template="plotly_white",
        color_discrete_map={"actual": "#2563eb", "plan": "#64748b"},
    )

    fig.update_traces(line_shape="spline", line=dict(width=4), marker=dict(size=10))
    fig.update_traces(
        patch={"line": {"dash": "dot", "width": 3}},
        selector={"name": "plan"},
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Actual: %{customdata[1]}<extra></extra>",
        customdata=chart_df[["label", "actual_fmt"]],
        selector={"name": "actual"},
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Plan: %{customdata[1]}<extra></extra>",
        customdata=chart_df[["label", "plan_fmt"]],
        selector={"name": "plan"},
    )

    for trace in fig.data:
        if trace.name == "actual":
            trace.name = "Actual"
        elif trace.name == "plan":
            trace.name = "Plan"

    fig.update_xaxes(
        title_text="Date" if trend_option == "Daily" else "Week Date",
        showgrid=True,
        gridwidth=1,
        gridcolor="#e5e7eb",
        griddash="dot",
        tickmode="array",
        tickvals=chart_df["period"],
        ticktext=chart_df["label"],
        tickangle=0,
        tickfont=dict(size=16, color="#000000", family="Inter"),
        title_font=dict(size=17, color="#000000", family="Inter"),
        automargin=True
    )

    fig.update_yaxes(
        title_text=metric_unit_label(metric),
        showgrid=True,
        gridwidth=1,
        gridcolor="#e5e7eb",
        tickfont=dict(size=15, color="#000000", family="Inter"),
        title_font=dict(size=17, color="#000000", family="Inter"),
    )

    fig.update_layout(
        height=400,
        margin=dict(l=50, r=20, t=70, b=70),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=15, color="#000000", family="Inter"),
            itemwidth=80,
            itemsizing="constant"
        ),
        legend_title_text="",
        font=dict(family="Inter", size=12, color="#000000"),
        title=dict(font=dict(size=18, color="#000000")),
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Inter",
            font_color="#000000",
            bordercolor="#e5e7eb",
        ),
        hovermode="x unified",
    )

    return fig


@st.cache_data(show_spinner=False)
def build_snapshot_chart(df_now, metric):
    decimal = get_metric_decimal(metric)
    agg = get_metric_agg(metric)
    label = METRIC_LABEL[metric]

    df_metric = df_now[df_now["metric"] == metric].copy()
    if df_metric.empty:
        return None

    if agg == "sum":
        snap_df = (
            df_metric.groupby("category", observed=True)[["actual", "plan"]]
            .sum()
            .reset_index()
        )
    else:
        snap_df = (
            df_metric.groupby("category", observed=True)[["actual", "plan"]]
            .mean()
            .reset_index()
        )

    snap_df["category"] = pd.Categorical(
        snap_df["category"],
        categories=CATEGORY_ORDER,
        ordered=True,
    )
    snap_df = snap_df.sort_values("category")

    chart_df = snap_df.melt(
        id_vars="category",
        value_vars=["actual", "plan"],
        var_name="Type",
        value_name="Value",
    )
    chart_df["Type"] = chart_df["Type"].replace({"actual": "Actual", "plan": "Plan"})
    chart_df["Label"] = chart_df["Value"].apply(lambda x: format_chart_text(x, decimal))

    if metric == "fuel_ratio":
        color_map = {"Actual": "#2563eb", "Plan": "#93c5fd"}
    else:
        color_map = {"Actual": "#ea580c", "Plan": "#fdba74"}

    fig = px.bar(
        chart_df,
        x="category",
        y="Value",
        text="Label",
        color="Type",
        color_discrete_map=color_map,
        barmode="group",
        template="plotly_white",
        title=f"Snapshot Weekly - {label}",
    )

    fig.update_traces(
        textposition="outside",
        textfont=dict(size=15, color="#000000", family="Inter"),
        marker=dict(
            opacity=0.95,
            line=dict(width=1, color="#ffffff")
        ),
        hovertemplate="<b>%{fullData.name}</b><br>%{y}<extra></extra>",
    )

    max_val = chart_df["Value"].max()
    max_val = max_val * 1.35 if pd.notna(max_val) and max_val > 0 else 1

    fig.update_layout(
        height=420,
        yaxis=dict(
            range=[0, max_val],
            title=metric_unit_label(metric),
            tickfont=dict(size=14, color="#000000", family="Inter"),
            title_font=dict(size=16, color="#000000", family="Inter"),
            gridcolor="#e5e7eb",
        ),
        xaxis=dict(
            title="Category",
            tickfont=dict(size=16, color="#000000", family="Inter"),
            title_font=dict(size=18, color="#000000", family="Inter"),
            tickangle=0,
            automargin=True
        ),
        margin=dict(l=50, r=20, t=60, b=100),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=15, color="#000000", family="Inter"),
            itemwidth=80,
            itemsizing="constant"
        ),
        legend_title_text="",
        title=dict(font=dict(size=20, color="#000000")),
        font=dict(family="Inter", size=14, color="#000000"),
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="#e5e7eb",
            font_size=14,
            font_family="Inter",
            font_color="#000000",
        ),
    )

    return fig


def build_delta_matrix(df_metric):
    if df_metric.empty:
        return pd.DataFrame()

    df = df_metric.copy()
    df["date_fmt"] = pd.to_datetime(df["date"]).dt.strftime("%d-%b")
    df["delta"] = df["actual"] - df["plan"]
    df["pct"] = df.apply(
        lambda x: ((x["actual"] - x["plan"]) / x["plan"] * 100) if x["plan"] != 0 else 0, 
        axis=1
    )

    pivot_delta = df.pivot_table(
        index="category",
        columns="date_fmt",
        values="delta",
        aggfunc="mean"
    )
    
    pivot_pct = df.pivot_table(
        index="category",
        columns="date_fmt",
        values="pct",
        aggfunc="mean"
    )

    available_cats = [c for c in CATEGORY_ORDER if c in pivot_delta.index]
    pivot_delta = pivot_delta.reindex(available_cats)
    pivot_pct = pivot_pct.reindex(available_cats)

    styled_rows = []
    for cat in pivot_delta.index:
        row = {"Category": cat}
        for col in pivot_delta.columns:
            val = pivot_delta.loc[cat, col]
            pct = pivot_pct.loc[cat, col]
            
            if pd.isna(val):
                row[col] = ""
                continue

            if abs(val) >= 1:
                val_fmt = format_number(val, 0)
            else:
                val_fmt = f"{val:.3f}"

            if val > 0:
                row[col] = f"🔴 +{val_fmt} ({pct:+.1f}%)"
            elif val < 0:
                row[col] = f"🟢 {val_fmt} ({pct:+.1f}%)"
            else:
                row[col] = f"⚪ 0 (0.0%)"
        styled_rows.append(row)

    styled_df = pd.DataFrame(styled_rows)
    return styled_df


# ==============================
# MAIN PAGE
# ==============================
def show_fuel_page(df, selected_block, selected_week):

    st.markdown("## ⛽ Fuel Analysis")

    if df is None or df.empty:
        st.warning("Tidak ada data fuel")
        return

    df = df.copy()

    required_cols = ["date", "week_date", "block", "category", "metric", "plan", "actual", "unit"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.warning(f"Kolom Fuel belum lengkap: {missing}")
        return

    # Data Preparation
    df["metric"] = df["metric"].astype(str).str.strip().str.lower()
    df["block"] = df["block"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["unit"] = df["unit"].astype(str).str.strip()
    df["actual"] = pd.to_numeric(df["actual"], errors="coerce").fillna(0)
    df["plan"] = pd.to_numeric(df["plan"], errors="coerce").fillna(0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["week_date"] = pd.to_datetime(df["week_date"], errors="coerce").dt.normalize()

    df = df.dropna(subset=["date", "week_date"])
    df = df[df["metric"].isin(METRIC_LABEL.keys())]

    # Global Filter: Block (Applied to main DF early for consistent charts & tables)
    if selected_block != "All":
        df = df[df["block"] == selected_block]

    if df.empty:
        st.warning(f"Data fuel tidak tersedia untuk block {selected_block}.")
        return

    current_week = pd.to_datetime(selected_week).normalize()
    df_now = df[df["week_date"] == current_week].copy()

    if df_now.empty:
        st.warning(f"Tidak ada data fuel untuk minggu {current_week.strftime('%d-%b-%Y')}")
        return

    # ===============================
    # KPI MODE (HANYA UNTUK CARD)
    # ===============================
    st.write("")
    kpi_mode = st.radio(
        "Mode KPI (Highlights Only)",
        ["Weekly", "MTD", "YTD", "Custom"],
        horizontal=True,
        key="fuel_kpi_mode"
    )

    custom_range = None
    if kpi_mode == "Custom":
        custom_range = st.date_input(
            "Pilih Range KPI",
            value=(current_week.date(), current_week.date()),
            key="fuel_custom_range"
        )

    # ===============================
    # KPI DATA SOURCE
    # ===============================
    df_kpi_source = df.copy() 
    df_kpi_source["date"] = pd.to_datetime(df_kpi_source["date"]).dt.normalize()

    if kpi_mode == "Weekly":
        df_kpi = df_now.copy()

    elif kpi_mode == "MTD":
        start_month = current_week.replace(day=1)
        df_kpi = df_kpi_source[
            (df_kpi_source["date"] >= start_month) &
            (df_kpi_source["date"] <= current_week)
        ]

    elif kpi_mode == "YTD":
        start_year = current_week.replace(month=1, day=1)
        df_kpi = df_kpi_source[
            (df_kpi_source["date"] >= start_year) &
            (df_kpi_source["date"] <= current_week)
        ]

    elif kpi_mode == "Custom" and custom_range and len(custom_range) == 2:
        start = pd.to_datetime(custom_range[0]).normalize()
        end = pd.to_datetime(custom_range[1]).normalize()
        df_kpi = df_kpi_source[
            (df_kpi_source["date"] >= start) &
            (df_kpi_source["date"] <= end)
        ]
    else:
        df_kpi = df_now.copy()

    if df_kpi.empty:
        df_kpi = df_now.copy()

    # Pre-calculate Previous Week for WoW (Always Weekly)
    all_weeks = sorted(df["week_date"].dropna().unique().tolist())
    prev_week = None
    if current_week in all_weeks:
        idx = all_weeks.index(current_week)
        if idx > 0:
            prev_week = all_weeks[idx - 1]
    
    df_prev = df[df["week_date"] == prev_week].copy() if prev_week else pd.DataFrame()

    # ============================================
    # 📊 KEY HIGHLIGHT - FUEL RATIO BY CATEGORY
    # ============================================
    st.markdown(f"### 📊 Key Highlight ({kpi_mode}) - Fuel Ratio by Category")
    
    # Caption showing the dynamic range
    st.caption(f"Data Range: {df_kpi['date'].min().strftime('%d %b')} - {df_kpi['date'].max().strftime('%d %b %Y')}")

    df_ratio_now = df_kpi[df_kpi["metric"] == "fuel_ratio"].copy()
    df_ratio_prev = df_prev[df_prev["metric"] == "fuel_ratio"].copy() if not df_prev.empty else pd.DataFrame()

    categories_now = [c for c in CATEGORY_ORDER if c in df_ratio_now["category"].dropna().unique().tolist()]
    categories_now += sorted([c for c in df_ratio_now["category"].dropna().unique().tolist() if c not in categories_now])

    if not categories_now:
        st.info("Data fuel ratio belum tersedia untuk periode ini.")
    else:
        for start_idx in range(0, len(categories_now), 3):
            cols = st.columns(3)
            for idx, cat in enumerate(categories_now[start_idx:start_idx + 3]):
                df_cat_now = df_ratio_now[df_ratio_now["category"] == cat]
                val_act = df_cat_now["actual"].mean()
                val_pln = df_cat_now["plan"].mean()

                val_prev = None
                if not df_ratio_prev.empty:
                    df_cat_prev = df_ratio_prev[df_ratio_prev["category"] == cat]
                    if not df_cat_prev.empty:
                        val_prev = df_cat_prev["actual"].mean()

                # WoW logic: Only show if Weekly mode is active
                if kpi_mode == "Weekly":
                    delta_wow = ((val_act - val_prev) / val_prev * 100) if val_prev and val_prev > 0 else None
                else:
                    delta_wow = None
                    
                delta_plan = ((val_act - val_pln) / val_pln * 100) if val_pln and val_pln > 0 else None

                with cols[idx]:
                    # PATCH: Menggunakan ratio_decimal (3) agar nilai presisi muncul di KPI Card
                    ratio_decimal = get_metric_decimal("fuel_ratio")
                    render_kpi_card(cat, format_number(val_act, ratio_decimal), delta_wow, delta_plan)

    # ============================================
    # DAILY FUEL RATIO (ALL CATEGORY) - WEEKLY BASIS
    # ============================================
    st.write("")
    with st.expander("⚡ Daily Fuel Ratio Analysis", expanded=False):
        st.markdown("### ⚡ Daily Fuel Ratio (Selected Week)")

        # Data for chart always uses df_now (Weekly)
        df_ratio_weekly = df_now[df_now["metric"] == "fuel_ratio"].copy()

        if not df_ratio_weekly.empty:
            daily_ratio = (
                df_ratio_weekly.groupby(["date", "category"])
                .agg({"actual": "mean", "plan": "mean"})
                .reset_index()
            )

            fig_ratio = px.bar(
                daily_ratio,
                x="date",
                y="actual",
                color="category",
                barmode="group",
                text=daily_ratio["actual"].round(2),
                title="Daily Fuel Ratio per Category",
                template="plotly_white"
            )

            fig_ratio.update_traces(
                textposition="outside",
                textfont=dict(size=14, color="#000000", family="Inter"),
                cliponaxis=False,
                hovertemplate="<b>%{fullData.name}</b><br>%{y:.2f}<extra></extra>"
            )

            fig_ratio.update_layout(
                height=450,
                margin=dict(l=50, r=20, t=80, b=60), 
                font=dict(family="Inter", size=14, color="#000000"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=13, color="#000000", family="Inter"),
                    itemwidth=70, itemsizing="constant"
                ),
                hoverlabel=dict(bgcolor="white", bordercolor="#e5e7eb", font_size=14, font_family="Inter", font_color="#000000"),
                xaxis=dict(title=None, tickfont=dict(size=14, color="#000000"), tickangle=0),
                yaxis=dict(title="Fuel Ratio", tickfont=dict(size=14, color="#000000"), showgrid=True, gridcolor="#e5e7eb")
            )

            st.plotly_chart(fig_ratio, use_container_width=True)

            st.caption("Deviation vs Plan (negative = efficient, positive = overconsumption)")
            with st.expander("📊 Daily Deviation from Plan (Fuel Ratio)", expanded=False):
                delta_table = build_delta_matrix(daily_ratio)
                render_clean_table(delta_table, height=400)

        else:
            st.info("Tidak ada data fuel ratio untuk minggu ini.")

        with st.expander("📋 Detail Fuel Ratio (Actual vs Plan)", expanded=False):
            if not df_ratio_weekly.empty:
                ratio_table = build_daily_detail_table(df_ratio_weekly, "fuel_ratio")
                render_clean_table(ratio_table, height=520)

    # ============================================
    # DAILY FUEL CONSUMPTION (ALL CATEGORY)
    # ============================================
    st.write("")
    with st.expander("⛽ Daily Fuel Consumption Analysis", expanded=False):
        st.markdown("### ⛽ Daily Fuel Consumption (Selected Week)")

        df_fuel_weekly = df_now[df_now["metric"] == "fuel"].copy()

        if not df_fuel_weekly.empty:
            daily_fuel = (
                df_fuel_weekly.groupby(["date", "category"])
                .agg({"actual": "sum", "plan": "sum"})
                .reset_index()
            )

            fig_fuel = px.bar(
                daily_fuel,
                x="date",
                y="actual",
                color="category",
                barmode="group",
                text=daily_fuel["actual"].apply(lambda x: format_number(x, 0)),
                title="Daily Fuel Consumption per Category",
                template="plotly_white"
            )

            fig_fuel.update_traces(
                textposition="outside",
                textfont=dict(size=14, color="#000000", family="Inter"),
                cliponaxis=False,
                hovertemplate="<b>%{fullData.name}</b><br>%{y:,.0f} L<extra></extra>"
            )

            fig_fuel.update_layout(
                height=450,
                margin=dict(l=50, r=20, t=80, b=60), 
                font=dict(family="Inter", size=14, color="#000000"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=13, color="#000000", family="Inter"),
                    itemwidth=70, itemsizing="constant"
                ),
                hoverlabel=dict(bgcolor="white", bordercolor="#e5e7eb", font_size=14, font_family="Inter", font_color="#000000"),
                xaxis=dict(title=None, tickfont=dict(size=14, color="#000000"), tickangle=0),
                yaxis=dict(title="Fuel (Liter)", tickfont=dict(size=14, color="#000000"), showgrid=True, gridcolor="#e5e7eb")
            )

            st.plotly_chart(fig_fuel, use_container_width=True)

            with st.expander("📊 Daily Deviation from Plan (Fuel Consumption)", expanded=False):
                delta_table_fuel = build_delta_matrix(daily_fuel)
                render_clean_table(delta_table_fuel, height=400)
        else:
            st.info("Tidak ada data fuel untuk minggu ini.")

        with st.expander("📋 Detail Fuel Liter (Actual vs Plan)", expanded=False):
            if not df_fuel_weekly.empty:
                fuel_table = build_daily_detail_table(df_fuel_weekly, "fuel")
                render_clean_table(fuel_table, height=520)

    # ============================================
    # 📈 TREND ACTUAL VS PLAN
    # ============================================
    st.write("")
    with st.expander("📈 Trend Analysis", expanded=False):
        st.markdown("### 📈 Trend Actual vs Plan")
        st.markdown("---")

        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)

        with col_ctrl1:
            trend_option = st.radio("Trend Type", ["Daily", "Weekly"], horizontal=True, key="fuel_trend_type")

        with col_ctrl2:
            trend_cats = sorted(df_now["category"].unique().tolist())
            category_filter = st.selectbox("Category Filter", ["All"] + trend_cats, key="fuel_trend_category")

        selected_range_trend = None
        if trend_option == "Weekly":
            with col_ctrl3:
                week_windows = []
                w_size = 8
                for i in range(0, len(all_weeks), w_size):
                    chunk = all_weeks[max(0, len(all_weeks) - (i + w_size)): len(all_weeks) - i]
                    if chunk:
                        label = f"{chunk[0].strftime('%d-%b')} → {chunk[-1].strftime('%d-%b')}"
                        week_windows.append({"label": label, "start": chunk[0], "end": chunk[-1]})
                if week_windows:
                    selected_range_trend = st.selectbox("Range Minggu", options=week_windows, format_func=lambda x: x["label"], key="fuel_week_range")

        trend_items = [("fuel_ratio", "Fuel Ratio"), ("fuel", "Fuel Liter")]
        for i in range(0, len(trend_items), 2):
            t_col1, t_col2 = st.columns(2)
            pair = trend_items[i:i + 2]
            for col, (m, l) in zip([t_col1, t_col2], pair):
                fig_trend = build_trend_chart(
                    df_source=df, metric=m, trend_option=trend_option, 
                    current_week=current_week, selected_range=selected_range_trend, 
                    category_filter=category_filter
                )
                with col:
                    if fig_trend: st.plotly_chart(fig_trend, use_container_width=True)
                    else: st.info(f"Tidak ada data trend untuk {l}.")

    # ============================================
    # 📊 SNAPSHOT WEEKLY
    # ============================================
    st.write("")
    with st.expander("📊 Weekly Snapshot", expanded=False):
        st.markdown("### 📊 Weekly Snapshot (Aggregation)")
        st.markdown("---")

        fig_snap_ratio = build_snapshot_chart(df_now, "fuel_ratio")
        if fig_snap_ratio:
            st.plotly_chart(fig_snap_ratio, use_container_width=True)

        st.write("")
        fig_snap_fuel = build_snapshot_chart(df_now, "fuel")
        if fig_snap_fuel:
            st.plotly_chart(fig_snap_fuel, use_container_width=True)

        st.divider()