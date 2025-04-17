import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils import (
    FETCH_LARGE_JUMPS_QUERY,
    UPDATE_LARGE_JUMPS_QUERY,
    FETCH_AFTER_LARGE_JUMP_QUERY,
    FETCH_BEFORE_LARGE_JUMP_QUERY,
    INSERT_LOG_QUERY,
    can_user_edit,
    get_cursor,
    get_log_entry,
    get_username,
)

USER_CAN_EDIT = can_user_edit()


def create_jump_plot(row, log_scale):
    # Prepare lists for the historical points (before previousObsDT)
    x_hist, y_hist = [], []

    # Fetch the past observations
    with get_cursor() as cursor:
        cursor.execute(
            FETCH_BEFORE_LARGE_JUMP_QUERY,
            {
                "siteID": row["siteID"],
                "Measure": row["measure"],
                "previousObsDT": row["previousObsDT"],
            },
        )
        hist_rows = cursor.fetchall()
    # The query returns points in descending order; reverse to chronological order.
    hist_rows = list(reversed(hist_rows))
    for hist_row in hist_rows:
        x_hist.append(hist_row["collDT"])
        y_hist.append(hist_row["valavg"])

    # Fetch the future observation if it exists
    with get_cursor() as cursor:
        cursor.execute(
            FETCH_AFTER_LARGE_JUMP_QUERY,
            {
                "siteID": row["siteID"],
                "Measure": row["measure"],
                "latestObsDT": row["latestObsDT"],
            },
        )
        fut_row = cursor.fetchone()
    # Correctly assign fut_row values if available
    if fut_row is not None:
        x_fut = [fut_row["collDT"]]
        y_fut = [fut_row["valavg"]]
    else:
        x_fut, y_fut = [], []

    # Prepare the jump segment points: previousObs and latestObs
    x_jump = [row["previousObsDT"], row["latestObsDT"]]
    y_jump = [row["previousObs"], row["latestObs"]]

    # Combine values for rendering entire plot
    all_x = x_hist + x_jump + x_fut
    all_y = y_hist + y_jump + y_fut

    # Create Plotly figure and add historical trace (default styling)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=all_x,
            y=all_y,
            mode="lines+markers",
            name="History",
            text=[f"{val:.2f}" for val in all_y],
            hoverinfo="text",
        )
    )

    # Add jump trace with red line and markers
    fig.add_trace(
        go.Scatter(
            x=x_jump,
            y=y_jump,
            mode="lines+markers",
            name="Jump",
            line=dict(color="red", width=2),
            marker=dict(color="red", size=8),
            text=[
                f"Previous: {row['previousObs']:.2f}",
                f"Latest: {row['latestObs']:.2f}",
            ],
            hoverinfo="text",
        )
    )

    # Set x-axis ticks to only show the points
    fig.update_layout(
        title=f"Large Jump for [{row['siteID']}] [{row['measure']}]",
        xaxis_title="Date",
        yaxis=dict(title="Value", type="log" if log_scale else "linear"),
        height=400,
        xaxis=dict(
            tickmode="array",
            tickvals=all_x,
            ticktext=[str(dt) for dt in all_x],
        ),
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
        with st.spinner("Submitting changes..."):
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
                            st.session_state.df_large_jumps.loc[selected_index],
                            edited_df.loc[selected_index],
                            "Large Jumps",
                        ),
                    )
                # Update local DataFrame with the edited values
                st.session_state.df_large_jumps.loc[selected_index, "actionItem"] = (
                    edited_df.loc[selected_index, "actionItem"]
                )

            st.session_state.show_success_toast = True
            print("dialog triggered re-render")
            st.rerun()


def app():
    if "show_success_toast" in st.session_state and st.session_state.show_success_toast:
        st.toast('Data successfully updated!', icon='✅')
        st.session_state.show_success_toast = False
    
    if "df_large_jumps" not in st.session_state:
        with st.spinner(
            "If the data cluster is cold starting, this may take up to 5 minutes",
            show_time=True,
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

        # checkbox widget for toggling log scale of plots
        log_scale = st.checkbox("Use log scale", value=True)
        for idx in selected_rows.selection.rows:
            row_data = filtered_df.iloc[idx]
            fig = create_jump_plot(row_data, log_scale)
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
