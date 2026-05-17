import streamlit as st


def apply_app_style():
    st.markdown(
        """
        <style>
        .main {
            padding-top: 0.5rem;
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
        }

        .sticky-header {
            position: sticky;
            top: 0;
            background: white;
            z-index: 999;
            padding-top: 0.2rem;
            padding-bottom: 0.8rem;
            border-bottom: 1px solid #e9edf3;
            margin-bottom: 1rem;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #e9edf3;
            border-radius: 12px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True
    )