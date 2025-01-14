import os
import streamlit as st
from azure.storage.blob import BlobServiceClient
import pandas as pd

from blob_utils import download_df, upload_df, get_blob_service_client_from_conn_str

DOWNLOAD_BLOB_FILENAME = "historical_unusual_measures.csv"

DOWNLOAD_CONTAINER_PATH = "hani"

BLOB_SERVICE_CLIENT = get_blob_service_client_from_conn_str()

ENCODINGS = ["utf-8", "utf-16be", "latin1"]


def app():
    if "df_large_jumps" not in st.session_state:
        historical_unusual_measures = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            DOWNLOAD_BLOB_FILENAME,
            ENCODINGS,
        )
        st.session_state.df_large_jumps = historical_unusual_measures

    # Filter the dataframe based on datasetID
    sites = st.session_state.df_large_jumps["datasetID"].unique()
    selected_sites = st.multiselect(
        "Select datasetIDs to filter by:", sites, default=sites
    )

    # Filter the dataframe based on the selected measures
    measures = st.session_state.df_large_jumps["measure"].unique()
    selected_measures = st.multiselect(
        "Select measures to filter by:", measures, default=measures
    )

    # Filter the dataframe based on the selected measures and datasetIDs
    filtered_df = st.session_state.df_large_jumps[
        st.session_state.df_large_jumps["measure"].isin(selected_measures)
        & st.session_state.df_large_jumps["datasetID"].isin(selected_sites)
    ]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "latestObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "previousObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
        },
    )


st.set_page_config(
    page_title="Large Jumps",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚠️ Large Jumps")
print("app re-render")
app()
