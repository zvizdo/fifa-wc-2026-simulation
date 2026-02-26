"""
DuckDB connection manager for the FIFA WC 2026 simulation database.
"""
import os
import duckdb
import streamlit as st


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wc2026_general.duckdb")


@st.cache_resource
def get_db() -> duckdb.DuckDBPyConnection:
    """Return a cached read-only DuckDB connection."""
    return duckdb.connect(DB_PATH, read_only=True)
