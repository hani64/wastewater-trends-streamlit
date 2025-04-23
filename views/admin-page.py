import os
import streamlit as st
import pandas as pd

from utils import FETCH_LOG_QUERY, DELETE_LOG_QUERY, get_cursor, get_user_info


def app():
    # Only allow a specific username to access this view
    if os.getenv(
        "DEVELOPMENT"
    ) != "TRUE" and "Wastewater_StreamLit_AdminPage" not in get_user_info().get(
        "groups"
    ):
        st.error("Access denied. You do not have permission to view this page.")
        return

    with st.spinner(
        "If the data cluster is cold starting, this may take up to 5 minutes",
        show_time=True,
    ):
        with get_cursor() as cursor:
            cursor.execute(FETCH_LOG_QUERY)
            rows = [row.asDict() for row in cursor.fetchall()]
            st.session_state.df_logs = pd.DataFrame(rows)

    st.write(
        "Select one or more rows below and click the delete button to remove the entry(ies)."
    )
    selected_rows = st.dataframe(
        st.session_state.df_logs,
        use_container_width=True,
        selection_mode="multi-row",
        on_select="rerun",
        hide_index=True,
    )

    selection = selected_rows.selection.get("rows", [])

    if selection and st.button("Delete Selected Row(s)", type="primary"):
        with get_cursor() as cursor:
            for idx in selection:
                row = st.session_state.df_logs.iloc[idx]
                cursor.execute(
                    DELETE_LOG_QUERY,
                    {
                        "User": row["User"],
                        "Time": row["Time"],
                        "Page": row["Page"],
                        "Location": row["Location"],
                        "SiteID": row["SiteID"],
                        "Measure": row["Measure"],
                        "EpiWeek": row["EpiWeek"],
                        "EpiYear": row["EpiYear"],
                        "ChangedColumn": row["ChangedColumn"],
                        "OldValue": row["OldValue"],
                        "NewValue": row["NewValue"],
                    },
                )
        # Remove the deleted rows from the local DataFrame
        st.session_state.df_logs = st.session_state.df_logs.drop(
            st.session_state.df_logs.index[selection]
        ).reset_index(drop=True)
        # st.success("Selected row(s) have been deleted.",)
        st.rerun()


st.set_page_config(
    page_title="Admin Page",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("📝 Admin Page")
app()
