import streamlit as st
import pandas as pd

from utils import (
    FETCH_MPOX_QUERY,
    UPDATE_MPOX_QUERY,
    INSERT_LOG_QUERY,
    can_user_edit,
    get_cursor,
    get_log_entry,
    get_username,
)


USER_CAN_EDIT = can_user_edit()


@st.dialog("Change Row Data")
def edit_data_form(selected_indices):
    columns = ["Location", "EpiYear", "EpiWeek", "Week_start", "g2r_label"]

    edited_df = st.data_editor(
        st.session_state.df_mpox.iloc[selected_indices],
        column_order=columns,
        column_config={
            "g2r_label": st.column_config.SelectboxColumn(
                "g2r_label",
                options=["Consistent Detection", "No Detection"],
                required=True,
            ),
            "EpiYear": st.column_config.TextColumn()
        },
        use_container_width=True,
        hide_index=True,
        disabled=("Location", "EpiYear", "EpiWeek", "Week_start"),
    )

    if st.button("Submit", type="primary"):
        for selected_index in selected_indices:
            with get_cursor() as cursor:
                # Update SQL DB with the edited values
                row = edited_df.loc[selected_index]
                cursor.execute(
                    UPDATE_MPOX_QUERY,
                    {
                        "g2r_label": row["g2r_label"],
                        "location": row["Location"],
                        "epi_week": float(row["EpiWeek"]),
                        "epi_year": float(row["EpiYear"]),
                        "week_start": row["Week_start"],
                    },
                )
                # Update SQL DB with the log entry
                cursor.execute(
                    INSERT_LOG_QUERY,
                    get_log_entry(
                        get_username(),
                        st.session_state.df_mpox.loc[selected_index],
                        edited_df.loc[selected_index],
                        "Mpox Trends",
                    ),
                )
            # Update local DataFrame with the edited values
            st.session_state.df_mpox.loc[selected_index, "g2r_label"] = edited_df.loc[
                selected_index, "g2r_label"
            ]

        print("dialog triggered re-render")
        st.rerun()


def app():
    if "df_mpox" not in st.session_state:
        with st.spinner(
            "If the data cluster is cold starting, this may take up to 5 minutes", show_time=True
        ):
            with get_cursor() as cursor:
                cursor.execute(FETCH_MPOX_QUERY)
                rows = [row.asDict() for row in cursor.fetchall()]
                st.session_state.df_mpox = pd.DataFrame(rows)

    # Create a dataframe where only a single-row is selectable
    selected_rows = st.dataframe(
        st.session_state.df_mpox,
        use_container_width=True,
        selection_mode="multi-row" if USER_CAN_EDIT else None,
        on_select="rerun" if USER_CAN_EDIT else "ignore",
        hide_index=True,
        column_config={
            "EpiYear": st.column_config.TextColumn(),
        }
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
