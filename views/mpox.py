import streamlit as st
import pandas as pd

from blob_utils import (
    download_df,
    upload_df,
    get_blob_service_client_from_conn_str,
    get_username,
    get_log_entry,
)

DOWNLOAD_BLOB_FILENAME = "wastewater-mpox.csv"
UPLOAD_BLOB_FILENAME = "wastewater-mpox.csv"

USER_CHANGES_LOG_FILENAME = "user_changes_log.csv"

DOWNLOAD_CONTAINER_PATH = "wastewater"
UPLOAD_CONTAINER_PATH = "wastewater"

BLOB_SERVICE_CLIENT = get_blob_service_client_from_conn_str()

ENCODINGS = ["utf-16be", "utf-8", "latin1"]


@st.dialog("Change Row Data")
def edit_data_form(selected_index):
    edited_df = st.data_editor(
        st.session_state.df_mpox.iloc[[selected_index]],
        column_order=["Location", "EpiYear", "Week_start", "g2r_label"],
        column_config={
            "g2r_label": st.column_config.SelectboxColumn(
                "g2r_label",
                options=["Consistent Detection", "No Detection"],
                required=True,
            ),
        },
        use_container_width=True,
        hide_index=True,
        disabled=["Location"],
    )

    if st.button("Submit", type="primary"):
        # re-download most up-to-date csv before editing and uploading
        st.session_state.df_mpox = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            DOWNLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

        username = get_username()
        log_entry = get_log_entry(
            username,
            st.session_state.df_mpox.loc[selected_index],
            edited_df.loc[selected_index],
            "Mpox Trends",
        )

        # Append the log entry to the log DataFrame
        st.session_state.log_df = pd.concat(
            [st.session_state.log_df, log_entry], ignore_index=True
        )

        # Save the log DataFrame to a CSV file
        upload_df(
            BLOB_SERVICE_CLIENT,
            st.session_state.log_df,
            UPLOAD_CONTAINER_PATH,
            "user_changes_log.csv",
            ["utf-8"],
        )

        # gotta make this more efficient later
        # st.session_state.df_mpox.loc[selected_index] = edited_df
        st.session_state.df_mpox.loc[selected_index, "Location"] = edited_df.loc[
            selected_index, "Location"
        ]
        st.session_state.df_mpox.loc[selected_index, "EpiYear"] = edited_df.loc[
            selected_index, "EpiYear"
        ]
        st.session_state.df_mpox.loc[selected_index, "Week_start"] = edited_df.loc[
            selected_index, "Week_start"
        ]
        st.session_state.df_mpox.loc[selected_index, "g2r_label"] = edited_df.loc[
            selected_index, "g2r_label"
        ]

        upload_df(
            BLOB_SERVICE_CLIENT,
            st.session_state.df_mpox,
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

    if "df_mpox" not in st.session_state:
        st.session_state.df_mpox = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            DOWNLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

    # Create a dataframe where only a single-row is selectable
    selected_row = st.dataframe(
        st.session_state.df_mpox,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
    )

    # Get the index of the selected row, iff a row is selected
    if selected_row.selection.get("rows", []):
        edit_data_form(selected_row.selection.rows[0])


st.set_page_config(
    page_title="Mpox Trends",
    page_icon="🦠",
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

st.title("🦠 Mpox Trends")
print("app re-render")
app()
st.markdown(
    """
## How to Use This App

1. Use the selection box on the left of any row to select the site you want to modify
2. The selected row will be highlighted to show it is active
3. Click on any field value in the "Change Row Data" dialog to modify it
5. Click "Submit" to save your changes

For any questions or issues, please contact the system administrator.
"""
)
