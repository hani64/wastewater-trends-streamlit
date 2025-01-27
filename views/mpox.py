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

ENCODINGS = ["utf-8", "utf-16be", "latin1"]

# will implement when user groups are set up
USER_CAN_EDIT = True


@st.dialog("Change Row Data")
def edit_data_form(selected_indices):
    columns = ["Location", "EpiYear", "Week_start", "g2r_label"]

    edited_df = st.data_editor(
        st.session_state.df_mpox.iloc[selected_indices],
        column_order=columns,
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
        for selected_index in selected_indices:
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
            # Update the dataframe with the edited values
            st.session_state.df_mpox.loc[selected_index, columns] = edited_df.loc[
                selected_index, columns
            ]

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
    selected_rows = st.dataframe(
        st.session_state.df_mpox,
        use_container_width=True,
        selection_mode="multi-row" if USER_CAN_EDIT else None,
        on_select="rerun" if USER_CAN_EDIT else "ignore",
        hide_index=True,
    )

    # Get the index of the selected row, iff a row is selected
    if USER_CAN_EDIT and selected_rows.selection.get("rows", []):
        if st.button("Edit Selected Row(s)", type="primary"):
            edit_data_form(selected_rows.selection.rows)


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

1. Use the selection box on the left of any row to select the site(s) you want to modify
2. The selected row(s) will be highlighted to show they are active
3. Click on the "Edit Selected Row(s)" button to open the "Change Row Data" dialog
4. Click on any field value in the "Change Row Data" dialog to modify it
5. Click "Submit" to save your changes

For any questions or issues, please contact the system administrator.
"""
)
