import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils import (
    FETCH_LARGE_JUMPS_QUERY,
    UPDATE_LARGE_JUMPS_QUERY,
    INSERT_LOG_QUERY,
    can_user_edit,
    get_cursor,
    get_log_entry,
    get_username,
)

USER_CAN_EDIT = can_user_edit()


def create_jump_plot(row):
    # Create figure
    fig = go.Figure()

    # Add points and connecting line
    fig.add_trace(
        go.Scatter(
            x=[row["previousObsDT"], row["latestObsDT"]],
            y=[row["previousObs"], row["latestObs"]],
            mode="lines+markers",
            name=row["measure"],
            text=[
                f"Previous: {row['previousObs']:.2f}",
                f"Latest: {row['latestObs']:.2f}",
            ],
            hoverinfo="text",
        )
    )

    # Update layout
    fig.update_layout(
        title=f"Large Jump for [{row['siteID']}] [{row['measure']}]",
        xaxis_title="Date",
        yaxis_title="Value",
        height=400,
        xaxis=dict(tickformat="%Y-%m-%d", dtick="D1"),  # Show daily ticks
    )
    return fig


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
        for selected_index in selected_indices:
            with get_cursor() as cursor:
                # Update SQL DB with the edited values
                row = edited_df.loc[selected_index]
                cursor.execute(
                    UPDATE_LARGE_JUMPS_QUERY,
                    {
                        "action_item": row["actionItem"],
                        "site_id": row["siteID"],
                        "dataset_id": row["datasetID"],
                        "measure": row["measure"],
                        "previous_obs_dt": row["previousObsDT"],
                        "latest_obs_dt": row["latestObsDT"],
                    },
                )
                # Update SQL DB with the log entry
                cursor.execute(
                    INSERT_LOG_QUERY,
                    get_log_entry(
                        get_username(),
                        st.session_state.df_large_jumps.loc[selected_index],
                        edited_df.loc[selected_index],
                        "Large Jumps",
                    ),
                )
            # Update local DataFrame with the edited values
            st.session_state.df_large_jumps.loc[selected_index, "actionItem"] = (
                edited_df.loc[selected_index, "actionItem"]
            )

        print("dialog triggered re-render")
        st.rerun()


def app():
    if "df_large_jumps" not in st.session_state:
        with st.spinner(
            "If the data cluster is cold starting, this may take up to 5 minutes", show_time=True
        ):
            with get_cursor() as cursor:
                cursor.execute(FETCH_LARGE_JUMPS_QUERY)
                rows = [row.asDict() for row in cursor.fetchall()]
                st.session_state.df_large_jumps = pd.DataFrame(rows)

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
        selection_mode="multi-row" if USER_CAN_EDIT else None,
        on_select="rerun" if USER_CAN_EDIT else "ignore",
        column_config={
            "latestObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "previousObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
        },
    )

    # Get the index of the selected row, iff a row is selected
    if USER_CAN_EDIT and selected_rows.selection.get("rows", []):
        if st.button("Edit Selected Row(s)", type="primary"):
            edit_data_form(selected_rows.selection.rows)
        for idx in selected_rows.selection.rows:
            row_data = filtered_df.iloc[idx]
            fig = create_jump_plot(row_data)
            st.plotly_chart(fig, use_container_width=True)


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
        | `actionItem`      | If this measure is supposed to be removed or kept (keep by default                              |
        """
)
