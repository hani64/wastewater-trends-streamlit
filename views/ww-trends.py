import streamlit as st
import pandas as pd
import plotly.express as px

from utils import (
    FETCH_WW_TRENDS_QUERY,
    INSERT_LOG_QUERY,
    UPDATE_WW_TRENDS_QUERY,
    can_user_edit,
    get_cursor,
    trigger_job_run,
    get_log_entry,
    get_username,
)


COLOR_MAP = {
    "High": "#FF6B6B",
    "Moderate": "#FFD700",
    "Low": "#90EE90",
    "Non-detect": "#ADD8E6",
    "NA1": "#D3D3D3",
    "NA2": "#A8A8A8",
}

USER_CAN_EDIT = can_user_edit()


def create_sunburst_graph(df: pd.DataFrame, measure: str) -> px.sunburst:
    df = df[df["measure"] == measure]

    labels = []
    parents = []
    values = []

    site_only_mask = (
        # First find all Site rows
        (df["Grouping"] == "Site")
        &
        # Then exclude locations that also have City records
        ~df["City"].isin(df[df["Grouping"] == "City"]["Location"].unique())
    )

    prov_to_abbr = {
        "Alberta": "AB",
        "British Columbia": "BC",
        "Manitoba": "MB",
        "New Brunswick": "NB",
        "Newfoundland and Labrador": "NL",
        "Nova Scotia": "NS",
        "Ontario": "ON",
        "Prince Edward Island": "PE",
        "Quebec": "QC",
        "Saskatchewan": "SK",
        "Northwest Territories": "NT",
        "Nunavut": "NU",
        "Yukon": "YT",
    }

    for i, row in df.iterrows():
        values.append(row["Viral_Activity_Level"])
        if row["Grouping"] == "Site":
            labels.append(row["Location"])
            parent = prov_to_abbr[row["Province"]] if site_only_mask[i] else row["City"]
            parents.append(parent)
        if row["Grouping"] == "City":
            labels.append(row["City"])
            parents.append(prov_to_abbr[row["Province"]])
        if row["Grouping"] == "Province":
            labels.append(prov_to_abbr[row["Province"]])
            parents.append("Canada")
        if row["Grouping"] == "Canada":
            labels.append("Canada")
            parents.append("")

    data = {"labels": labels, "parents": parents, "values": values}

    # Convert to a DataFrame
    data = pd.DataFrame(data)

    fig = px.sunburst(
        data,
        names="labels",
        parents="parents",
        color="values",
        hover_data=["values"],
        color_discrete_map=COLOR_MAP,
        title=f"Wastewater Viral Activity Levels by Region - {measure}",
        width=800,
        height=800,
    )
    fig.update_traces(hovertemplate="%{customdata[0]}", leaf=dict(opacity=1))
    fig.update_layout(title_x=0.4)
    return fig


@st.dialog("Change Row Data")
def edit_data_form(selected_indices):
    columns = [
        "Location",
        "measure",
        "latestTrends",
        "LatestLevel",
        "Grouping",
        "City",
        "Province",
        "Viral_Activity_Level",
    ]

    edited_df = st.data_editor(
        st.session_state.df_ww.iloc[selected_indices],
        column_order=columns,
        column_config={
            "Viral_Activity_Level": st.column_config.SelectboxColumn(
                "Viral_Activity_Level",
                options=["High", "Moderate", "Low", "Non-detect", "NA1", "NA2"],
                required=True,
            )
        },
        use_container_width=True,
        hide_index=True,
        disabled=(
            "Location",
            "measure",
            "latestTrends",
            "LatestLevel",
            "Grouping",
            "City",
            "Province",
        ),
        key="edited_data_ww",
    )

    if st.session_state.edited_data_ww["edited_rows"] and st.button(
        "Submit", type="primary"
    ):
        log_entries = []
        for selected_index in selected_indices:
            with get_cursor() as cursor:
                # Update SQL DB with edited values
                row = edited_df.loc[selected_index]
                cursor.execute(
                    UPDATE_WW_TRENDS_QUERY,
                    {
                        "viral_activity_level": row["Viral_Activity_Level"],
                        "location": row["Location"],
                        "measure": row["measure"],
                        "city": row["City"],
                        "province": row["Province"],
                    },
                )
                # Update SQL DB with the log entry
                cursor.execute(
                    INSERT_LOG_QUERY,
                    get_log_entry(
                        st.session_state.df_ww.loc[selected_index],
                        edited_df.loc[selected_index],
                        "Water Wastewater Trends",
                    ),
                )
                log_entries.append(
                    get_log_entry(
                        st.session_state.df_ww.loc[selected_index],
                        edited_df.loc[selected_index],
                        "Water Wastewater Trends",
                    )
                )
            # Update the dataframe with the edited values
            st.session_state.df_ww.loc[selected_index, "Viral_Activity_Level"] = (
                edited_df.loc[selected_index, "Viral_Activity_Level"]
            )
        trigger_job_run("ww-trends", log_entries)

        print("dialog triggered re-render")
        st.rerun()


def app():
    if "df_ww" not in st.session_state:
        with st.spinner(
            "If the data cluster is cold starting, this may take up to 5 minutes",
            show_time=True,
        ):
            with get_cursor() as cursor:
                cursor.execute(FETCH_WW_TRENDS_QUERY)
                rows = [row.asDict() for row in cursor.fetchall()]
                st.session_state.df_ww = pd.DataFrame(rows)

    if "measure" not in st.session_state:
        st.session_state.measure = "covN2"

    left, right = st.columns([4, 1], vertical_alignment="center")

    left.plotly_chart(
        create_sunburst_graph(st.session_state.df_ww, st.session_state.measure),
        use_container_width=True,
    )

    legend = pd.DataFrame(
        list(COLOR_MAP.items()), columns=["Viral Activity Level", "Color"]
    )
    legend = legend.style.map(
        lambda x: f"background-color: {x}", subset="Color"
    ).format("", subset="Color")
    right.dataframe(
        legend,
        column_config={
            "Color": st.column_config.Column(
                width="small",
            )
        },
        hide_index=True,
    )

    selected = right.radio(
        label="**Select measure:**",
        options=["covN2", "rsv", "fluA", "fluB"],
        key="measure_select",
    )
    if selected != st.session_state.measure:
        st.session_state.measure = selected
        st.rerun()

    # Filter the dataframe based on all sites
    sites = st.session_state.df_ww["Location"].unique()
    sites = ["All Sites"] + list(sites)
    selected_sites = st.multiselect(
        "Select sites to filter by:", sites, default=["All Sites"]
    )
    # Filter the dataframe based on the selected measures
    measures = st.session_state.df_ww["measure"].unique()
    selected_measures = st.multiselect(
        "Select measures to filter by:", measures, default=measures
    )
    # Filter the dataframe based on the selected measures and sites
    if "All Sites" in selected_sites:
        filtered_df = st.session_state.df_ww[
            st.session_state.df_ww["measure"].isin(selected_measures)
        ]
    else:
        filtered_df = st.session_state.df_ww[
            st.session_state.df_ww["measure"].isin(selected_measures)
            & st.session_state.df_ww["Location"].isin(selected_sites)
        ]

    # Create a dataframe where only a single-row is selectable
    selected_rows = st.dataframe(
        filtered_df,
        use_container_width=True,
        selection_mode="multi-row" if USER_CAN_EDIT else None,
        on_select="rerun" if USER_CAN_EDIT else "ignore",
        hide_index=True,
        column_order=[
            "Location",
            "measure",
            "latestTrends",
            "LatestLevel",
            "Grouping",
            "City",
            "Province",
            "Viral_Activity_Level",
        ],
    )

    # Get the index of the selected row, iff a row is selected
    if USER_CAN_EDIT and selected_rows.selection.get("rows", []):
        if st.button("Edit Selected Row(s)", type="primary"):
            edit_data_form(filtered_df.index[selected_rows.selection.rows])


st.set_page_config(
    page_title="Respiratory Virus Trends",
    page_icon="🚰",
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

st.title("🚰 Respiratory Virus Trends")
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
