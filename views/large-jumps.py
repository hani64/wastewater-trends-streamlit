import streamlit as st
from azure.storage.blob import BlobServiceClient
import pandas as pd

from blob_utils import (
    download_df,
    get_log_entry,
    get_username,
    upload_df,
    get_blob_service_client_from_conn_str,
)

DOWNLOAD_BLOB_FILENAME = "historical_unusual_measures.csv"
UPLOAD_BLOB_FILENAME = "historical_unusual_measures.csv"

USER_CHANGES_LOG_FILENAME = "user_changes_log.csv"

DOWNLOAD_CONTAINER_PATH = "wastewater"
UPLOAD_CONTAINER_PATH = "wastewater"

BLOB_SERVICE_CLIENT = get_blob_service_client_from_conn_str()

ENCODINGS = ["utf-8", "utf-16be", "latin1"]


@st.dialog("Change Row Data")
def edit_data_form(selected_indices):
    edited_df = st.data_editor(
        st.session_state.df_large_jumps.iloc[selected_indices],
        use_container_width=True,
        hide_index=True,
        disabled=(
            "siteID",
            "datasetID",
            "measure",
            "fraction",
            "previousObs",
            "latestObs",
            "previousObsDT",
            "latestObsDT",
            "alertType",
        ),
        column_config={
            "latestObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "previousObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "actionItem": st.column_config.SelectboxColumn(
                "actionItem",
                options=["keep", "remove"],
                required=True,
            ),
            "fraction": None,
        },
    )

    if st.button("Submit", type="primary"):
        # re-download most up-to-date csv before editing and uploading
        st.session_state.df_large_jumps = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            DOWNLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

        username = get_username()
        for selected_index in selected_indices:
            log_entry = get_log_entry(
                username,
                st.session_state.df_large_jumps.loc[selected_index],
                edited_df.loc[selected_index],
                "Large Jumps",
            )
            # Append the log entry to the log DataFrame
            st.session_state.log_df = pd.concat(
                [st.session_state.log_df, log_entry], ignore_index=True
            )
            # Update the dataframe with the edited values
            st.session_state.df_large_jumps.loc[selected_index, "actionItem"] = (
                edited_df.loc[selected_index, "actionItem"]
            )

        # Save the log DataFrame to a CSV file
        upload_df(
            BLOB_SERVICE_CLIENT,
            st.session_state.log_df,
            UPLOAD_CONTAINER_PATH,
            "user_changes_log.csv",
            ["utf-8"],
        )
        # Save the edited DataFrame to a CSV file
        upload_df(
            BLOB_SERVICE_CLIENT,
            st.session_state.df_large_jumps,
            UPLOAD_CONTAINER_PATH,
            UPLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

        print("dialog triggered re-render")
        st.rerun()


def app():
    # Initialize the log DataFrame if it doesn't exist
    if "log_df" not in st.session_state:
        st.session_state.log_df = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            USER_CHANGES_LOG_FILENAME,
            ENCODINGS,
        )

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

    selected_rows = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row",
        on_select="rerun",
        column_config={
            "latestObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "previousObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "fraction": None,
        },
    )

    # Get the index of the selected row, iff a row is selected
    if selected_rows.selection.get("rows", []):
        if st.button("Edit Selected Row(s)", type="primary"):
            edit_data_form(selected_rows.selection.rows)

    st.markdown(
        """
        NOTE: `latestObsDT` shows when the latest **abnormal measure was observed**.
        This is **NOT** the latest observation date in the dataset for that site and measure.
        Refer to [Latest Measures](/latest-measures) for that information.

        ## Glossary
        | Column            | Description                                                                                     |
        |-------------------|-------------------------------------------------------------------------------------------------|
        | `siteID`          | The site ID.                                                                                    |
        | `datasetID`       | The dataset ID.                                                                                 |
        | `measure`         | The measure name.                                                                               |
        | `fraction`        | `liq` or `sol`                                                                                  |
        | `previousObs`     | The measure value that was observed before `latestObs`.                                         |
        | `latestObs`       | The measure value that was identified as a `largeJump` or `newMax`.                             |
        | `previousObsDT`   | The date at which the `previousObs` was observed.                                               |
        | `latestObsDT`     | The date at which `latestObs` was observed.                                                     |
        | `alert_type`      | The type of alert that was triggered:                                                           |
        |                   |  • `largeJump`: if difference between log10(`latestObs`) and log10(`previousObs`) is > 1        |
        |                   |  • `newMax`: if `latestObs` is > historical maximum recorded for that site and measure          |
        """
    )


st.set_page_config(
    page_title="Large Jumps",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# hack to make the dialog box wider
st.markdown(
    """
    <style>
        div[data-testid="stDialog"] div[role="dialog"] {
            width: 80%;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚠️ Large Jumps")
print("app re-render")
app()
