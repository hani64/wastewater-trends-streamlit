import os
import streamlit as st
from azure.storage.blob import BlobServiceClient
import pandas as pd
import plotly.express as px

from blob_utils import download_df, upload_df, get_blob_service_client_from_conn_str


DOWNLOAD_BLOB_FILENAME = "wastewater-trend-out.csv"
UPLOAD_BLOB_FILENAME = "wastewater-trend-out.csv"

DOWNLOAD_CONTAINER_PATH = "hani"
UPLOAD_CONTAINER_PATH = "hani"

BLOB_SERVICE_CLIENT = get_blob_service_client_from_conn_str()

ENCODINGS = ["utf-8", "latin1", "utf-16be"]

COLOR_MAP = {
    "High": "#FF6B6B",
    "Moderate": "#FFD700",
    "Low": "#90EE90",
    "Non-detect": "#ADD8E6",
    "NA1": "#D3D3D3",
    "NA2": "#A8A8A8",
}


def create_sunburst_graph(df: pd.DataFrame, measure: str) -> px.sunburst:
    df = df[df["measure"] == measure]
    # convert Viral_Activity_Level to a categorical order
    # viral_activity_order = ["NA2", "Non-detect", "Low", "Moderate", "High"]
    # df.loc[:, "Viral_Activity_Level"] = pd.Categorical(df["Viral_Activity_Level"], categories=viral_activity_order, ordered=True)

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
def edit_data_form(selected_index, csv=f"./{DOWNLOAD_BLOB_FILENAME}"):
    edited_df = st.data_editor(
        st.session_state.df_ww.iloc[[selected_index]],
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
        column_config={
            "Viral_Activity_Level": st.column_config.SelectboxColumn(
                "Viral_Activity_Level",
                options=["High", "Moderate", "Low", "Non-detect", "NA1", "NA2"],
                required=True,
            )
        },
        use_container_width=True,
        hide_index=True,
        disabled=("Location", "measure", "Grouping", "City", "Province"),
    )

    if st.button("Submit", type="primary"):
        # re-download most up-to-date csv before editing and uploading
        st.session_state.df_ww = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            DOWNLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

        # gotta make this more efficient later
        # st.session_state.df_ww.loc[selected_index] = edited_df
        st.session_state.df_ww.loc[selected_index, "Location"] = edited_df.loc[
            selected_index, "Location"
        ]
        st.session_state.df_ww.loc[selected_index, "measure"] = edited_df.loc[
            selected_index, "measure"
        ]
        st.session_state.df_ww.loc[selected_index, "latestTrends"] = edited_df.loc[
            selected_index, "latestTrends"
        ]
        st.session_state.df_ww.loc[selected_index, "LatestLevel"] = edited_df.loc[
            selected_index, "LatestLevel"
        ]
        st.session_state.df_ww.loc[selected_index, "Grouping"] = edited_df.loc[
            selected_index, "Grouping"
        ]
        st.session_state.df_ww.loc[selected_index, "City"] = edited_df.loc[
            selected_index, "City"
        ]
        st.session_state.df_ww.loc[selected_index, "Province"] = edited_df.loc[
            selected_index, "Province"
        ]
        st.session_state.df_ww.loc[selected_index, "Viral_Activity_Level"] = (
            edited_df.loc[selected_index, "Viral_Activity_Level"]
        )

        # upload_wastewater_trends(st.session_state.df_ww)
        upload_df(
            BLOB_SERVICE_CLIENT,
            st.session_state.df_ww,
            UPLOAD_CONTAINER_PATH,
            UPLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

        print("dialog triggered re-render")
        st.rerun()


def app():
    if "df_ww" not in st.session_state:
        st.session_state.df_ww = download_df(
            BLOB_SERVICE_CLIENT,
            DOWNLOAD_CONTAINER_PATH,
            DOWNLOAD_BLOB_FILENAME,
            ENCODINGS,
        )

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
    selected_row = st.dataframe(
        filtered_df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
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
    if selected_row.selection.get("rows", []):
        edit_data_form(filtered_df.index[selected_row.selection.rows[0]])


st.set_page_config(
    page_title="Wastewater Trends",
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

st.title("🚰 Wastewater Trends")
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
