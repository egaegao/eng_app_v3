import streamlit as st
import pandas as pd

# PATCH 2: st.set_page_config harus paling awal sebelum command streamlit lainnya
st.set_page_config(
    page_title="OPSAPP",
    page_icon="⛏️",
    layout="wide"
)

# Menampilkan detail error di client (Rekomendasi Bonus)
st.set_option('client.showErrorDetails', True)

from scripts.styles import apply_app_style
from scripts.loader import load_excel_data
from scripts.dashboard_pages.production_page import show_production_page
from scripts.dashboard_pages.hauling_page import show_hauling_page
from scripts.dashboard_pages.fleet_page import show_fleet_page
from scripts.dashboard_pages.unjuk_kerja import show_unjuk_kerja_page
# PATCH: Import Halaman EWH (Modul 5)
from scripts.dashboard_pages.ewh_page import show_ewh_page
# PATCH: Import Halaman Productivity (Modul 6)
from scripts.dashboard_pages.productivity_page import show_productivity_page
# PATCH: Import Halaman Weather (Modul 7)
from scripts.dashboard_pages.weather_page import show_weather_page
# PATCH: Import Halaman Inventory (Modul 8)
from scripts.dashboard_pages.inventory_page import show_inventory_page
# PATCH: Import Halaman Fuel (Modul 9)
from scripts.dashboard_pages.fuel_page import show_fuel_page

# PATCH: Import Halaman Modul 10, 11, 12
from scripts.dashboard_pages.issue_page import show_issue_page
from scripts.dashboard_pages.action_page import show_action_page
from scripts.dashboard_pages.findings_page import show_findings_page

def format_week_option(x):
    # Logika "All" tetap dipertahankan agar tidak error 
    if x == "All":
        return "All"
    return pd.to_datetime(x).strftime("%d-%b-%Y")

# Optimalisasi Global Filter (REVISI FINAL: SAFE VERSION)
def apply_global_filter(df, block):
    if df is None or df.empty:
        return df
    
    # Menambahkan pengecekan keberadaan kolom 'block' untuk mencegah crash
    if block is not None and "block" in df.columns:
        return df[df["block"] == block]
    
    return df

apply_app_style()

st.markdown('<div class="sticky-header">', unsafe_allow_html=True)

st.title("⛏️ OPSAPP - Mining Dashboard")

uploaded_files = st.file_uploader(
    "Upload File Excel (bisa multi file)",
    type=["xlsx"],
    accept_multiple_files=True
)

# ===============================================
# PATCH 1: FILE SIGNATURE DETECTION (RELOAD SAFETY)
# ===============================================
current_upload_signature = tuple(
    (file.name, getattr(file, "size", None)) for file in uploaded_files
) if uploaded_files else None

if "upload_signature" not in st.session_state:
    st.session_state.upload_signature = None

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False

if "df_storage" not in st.session_state:
    st.session_state.df_storage = {}

# Inisialisasi cache filter di session_state
if "block_options" not in st.session_state:
    st.session_state.block_options = []
if "week_options" not in st.session_state:
    st.session_state.week_options = []

# Jika signature berbeda (user ganti/tambah/kurangi file), reset state
if current_upload_signature != st.session_state.upload_signature:
    st.session_state.data_loaded = False
    st.session_state.df_storage = {}
    st.session_state.block_options = []
    st.session_state.week_options = []
    st.session_state.upload_signature = current_upload_signature

# Inisialisasi variabel data agar tidak error saat dipanggil di filter
df_all = None
df_produksi = None
df_hauling = None
df_fleet = None
df_unit = None
df_productivity = None
df_weather = None
df_inventory = None
df_fuel = None
df_issue = None
df_action = None
df_finding = None

# ===============================================
# PROSES LOAD DATA
# ===============================================
if uploaded_files and not st.session_state.data_loaded:
    df_list = []
    df_weather_list = [] 

    for file in uploaded_files:
        if "weather" in file.name.lower():
            try:
                temp_df = load_excel_data(file)
                df_weather_list.append(temp_df)
            except Exception as e:
                st.error(f"Gagal membaca file weather {file.name}: {e}")
        else:
            try:
                temp_df = load_excel_data(file)
                df_list.append(temp_df)
            except Exception as e:
                st.error(f"Gagal membaca file {file.name}: {e}")

    # 1. BUILD WEATHER TERPISAH
    if df_weather_list:
        df_weather = pd.concat(df_weather_list, ignore_index=True, sort=False)
        if "metric" in df_weather.columns:
            df_weather["metric"] = df_weather["metric"].astype(str).str.strip().str.lower()
            df_weather = df_weather[df_weather["metric"].notna()]
            df_weather = df_weather[df_weather["metric"] != "nan"]
            df_weather["actual"] = pd.to_numeric(df_weather["actual"], errors="coerce").fillna(0)
            df_weather["plan"] = pd.to_numeric(df_weather["plan"], errors="coerce").fillna(0)
    else:
        df_weather = None

    # 2. BUILD DATA MODUL LAINNYA
    if df_list:
        df_all = pd.concat(df_list, ignore_index=True, sort=False)
        df_all = df_all.dropna(how="all")
        
        if "metric_group" in df_all.columns:
            df_all["metric_group"] = df_all["metric_group"].astype(str).str.strip().str.lower()
            
            df_produksi = df_all[df_all["metric_group"] == "produksi"]
            df_hauling = df_all[df_all["metric_group"] == "hauling"]
            df_fleet = df_all[df_all["metric_group"] == "fleet"]
            df_unit = df_all[df_all["metric_group"] == "unit"]
            df_productivity = df_all[df_all["metric_group"] == "productivity"]
            df_inventory = df_all[df_all["metric_group"] == "inventory"]
            df_fuel = df_all[df_all["metric_group"] == "fuel"]
            df_issue = df_all[df_all["metric_group"] == "issue"]
            df_action = df_all[df_all["metric_group"] == "action"]
            df_finding = df_all[df_all["metric_group"] == "finding"]
        else:
            st.warning("Kolom 'metric_group' tidak ditemukan dalam file utama.")
    else:
        df_all = None

    # CACHE FILTER OPTIONS
    combined_for_filter_list = []
    if df_all is not None: combined_for_filter_list.append(df_all)
    if df_weather is not None: combined_for_filter_list.append(df_weather)

    if combined_for_filter_list:
        df_filter_temp = pd.concat(combined_for_filter_list, ignore_index=True, sort=False)

        # BLOCK OPTIONS
        if "block" in df_filter_temp.columns:
            st.session_state.block_options = sorted(
                df_filter_temp["block"].dropna().astype(str).str.strip().unique().tolist()
            )

        # WEEK OPTIONS
        if "week_date" in df_filter_temp.columns:
            st.session_state.week_options = sorted(
                pd.to_datetime(df_filter_temp["week_date"], errors="coerce")
                .dropna()
                .dt.normalize()
                .unique()
                .tolist()
            )
    else:
        st.session_state.block_options = []
        st.session_state.week_options = []

    st.session_state.df_storage = {
        "df_all": df_all,
        "df_produksi": df_produksi,
        "df_hauling": df_hauling,
        "df_fleet": df_fleet,
        "df_unit": df_unit,
        "df_productivity": df_productivity,
        "df_weather": df_weather,
        "df_inventory": df_inventory,
        "df_fuel": df_fuel,
        "df_issue": df_issue,
        "df_action": df_action,
        "df_finding": df_finding
    }
    st.session_state.data_loaded = True

# LOAD DARI SESSION
if st.session_state.data_loaded:
    df_all = st.session_state.df_storage.get("df_all")
    df_produksi = st.session_state.df_storage.get("df_produksi")
    df_hauling = st.session_state.df_storage.get("df_hauling")
    df_fleet = st.session_state.df_storage.get("df_fleet")
    df_unit = st.session_state.df_storage.get("df_unit")
    df_productivity = st.session_state.df_storage.get("df_productivity")
    df_weather = st.session_state.df_storage.get("df_weather")
    df_inventory = st.session_state.df_storage.get("df_inventory")
    df_fuel = st.session_state.df_storage.get("df_fuel")
    df_issue = st.session_state.df_storage.get("df_issue")
    df_action = st.session_state.df_storage.get("df_action")
    df_finding = st.session_state.df_storage.get("df_finding")

# Reset data jika file uploader dikosongkan
if not uploaded_files and st.session_state.data_loaded:
    st.session_state.data_loaded = False
    st.session_state.df_storage = {}
    st.session_state.block_options = []
    st.session_state.week_options = []
    st.session_state.upload_signature = None
    st.rerun()

# ===============================================
# BARIS FILTER GLOBAL (3 KOLOM)
# ===============================================
col1, col2, col3 = st.columns(3)

with col1:
    block_options = st.session_state.get("block_options", [])
    # REVISI FINAL: Kondisi eksplisit untuk selectbox block
    if block_options:
        selected_block = st.selectbox(
            "Pilih Block",
            options=block_options,
            index=0
        )
    else:
        selected_block = None

with col2:
    week_options = st.session_state.get("week_options", [])
    # REVISI FINAL: Kondisi eksplisit untuk selectbox week
    if week_options:
        selected_week = st.selectbox(
            "Pilih Week",
            options=week_options,
            index=0,
            format_func=format_week_option
        )
    else:
        selected_week = None

with col3:
    category_all_data = []
    if df_unit is not None and not df_unit.empty:
        category_all_data.extend(df_unit["category"].dropna().unique().tolist())
    if df_productivity is not None and not df_productivity.empty:
        category_all_data.extend(df_productivity["category"].dropna().unique().tolist())
    
    if category_all_data:
        category_list = ["All"] + sorted(list(set(category_all_data)))
    else:
        category_list = ["All"]

    selected_category_global = st.selectbox(
        "Filter Category (Unit, EWH, Productivity)",
        options=category_list,
        index=0
    )

st.markdown('</div>', unsafe_allow_html=True)

# ===============================================
# NAVIGASI MENU (RADIO BUTTON)
# ===============================================
selected_page = st.radio(
    "Pilih Modul Dashboard",
    [
        "📊 Produksi", 
        "🚛 Hauling", 
        "🚜 Fleet", 
        "🚜 Unjuk Kerja",
        "⏱️ EWH",
        "⚡ Productivity",
        "🌧️ Weather",
        "📦 Inventory",
        "⛽ Fuel",
        "⚠️ Issue",
        "🛠️ Action",
        "📋 Findings"
    ],
    horizontal=True
)

st.divider()

# ==================================================================
# RENDER HALAMAN AKTIF - LAZY FILTERING
# ==================================================================
try:
    if selected_page == "📊 Produksi":
        if df_produksi is None or df_produksi.empty:
            st.info("Data produksi belum diupload")
        else:
            df_produksi_f = apply_global_filter(df_produksi, selected_block)
            show_production_page(df_produksi_f, selected_block, selected_week)

    elif selected_page == "🚛 Hauling":
        if df_hauling is None or df_hauling.empty:
            st.info("Data hauling belum diupload")
        else:
            df_hauling_f = apply_global_filter(df_hauling, selected_block)
            show_hauling_page(df_hauling_f, selected_block, selected_week)

    elif selected_page == "🚜 Fleet":
        if df_fleet is None or df_fleet.empty:
            st.info("Data fleet belum diupload")
        else:
            df_fleet_f = apply_global_filter(df_fleet, selected_block)
            show_fleet_page(df_fleet_f, selected_block, selected_week)

    elif selected_page == "🚜 Unjuk Kerja":
        if df_unit is None or df_unit.empty:
            st.info("Data unit belum diupload")
        else:
            df_unit_f = apply_global_filter(df_unit, selected_block)
            show_unjuk_kerja_page(df_unit_f, selected_block, selected_week, selected_category_global)

    elif selected_page == "⏱️ EWH":
        if df_unit is None or df_unit.empty:
            st.info("Data EWH belum diupload")
        else:
            df_unit_f = apply_global_filter(df_unit, selected_block)
            show_ewh_page(df_unit_f, selected_block, selected_week, selected_category_global)

    elif selected_page == "⚡ Productivity":
        if df_productivity is None or df_productivity.empty:
            st.info("Data productivity belum diupload")
        else:
            df_productivity_f = apply_global_filter(df_productivity, selected_block)
            show_productivity_page(df_productivity_f, selected_block, selected_week, selected_category_global)

    elif selected_page == "🌧️ Weather":
        if df_weather is None or df_weather.empty:
            st.info("Data weather belum diupload (Pastikan nama file mengandung kata 'weather')")
        else:
            df_weather_f = apply_global_filter(df_weather, selected_block)
            show_weather_page(df_weather_f, selected_block, selected_week)

    elif selected_page == "📦 Inventory":
        if df_inventory is None or df_inventory.empty:
            st.info("Data inventory belum diupload")
        else:
            df_inventory_f = apply_global_filter(df_inventory, selected_block)
            show_inventory_page(df_inventory_f, selected_block, selected_week)

    elif selected_page == "⛽ Fuel":
        if df_fuel is None or df_fuel.empty:
            st.info("Data fuel belum diupload")
        else:
            df_fuel_f = apply_global_filter(df_fuel, selected_block)
            show_fuel_page(df_fuel_f, selected_block, selected_week)

    elif selected_page == "⚠️ Issue":
        if df_issue is None or df_issue.empty:
            st.info("Data issue belum diupload")
        else:
            df_issue_f = apply_global_filter(df_issue, selected_block)
            show_issue_page(df_issue_f, selected_block, selected_week)

    elif selected_page == "🛠️ Action":
        if df_action is None or df_action.empty:
            st.info("Data action belum diupload")
        else:
            df_action_f = apply_global_filter(df_action, selected_block)
            show_action_page(df_action_f, selected_block, selected_week)

    elif selected_page == "📋 Findings":
        if df_finding is None or df_finding.empty:
            st.info("Data findings belum diupload")
        else:
            df_finding_f = apply_global_filter(df_finding, selected_block)
            show_findings_page(df_finding_f, selected_block, selected_week)

except Exception as e:
    st.error(f"Terjadi kesalahan saat memuat modul {selected_page}: {e}")