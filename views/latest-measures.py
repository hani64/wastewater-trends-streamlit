import os
import pandas as pd
import streamlit as st
from azure.storage.blob import BlobServiceClient
import time

from blob_utils import download_df, get_blob_service_client_from_conn_str


DOWNLOAD_BLOB_FILENAME = "allSites.csv"

DOWNLOAD_CONTAINER_PATH = "wastewater"

ENCODING_ALL_SITES = os.getenv("ENCODING_ALL_SITES", default="utf-8")

BLOB_SERVICE_CLIENT = get_blob_service_client_from_conn_str()

ENCODINGS = ["utf-8", "utf-16be", "latin1"]


def get_latest_obs_df(all_sites):
    # convert collDT to datetime
    all_sites["collDT"] = pd.to_datetime(all_sites["collDT"])
    # remove rows that have conf measures
    all_sites = all_sites.loc[~all_sites["measure"].str.startswith("conf")]
    # subset of allSite with only relevant columns
    all_sites_sub = all_sites[
        [
            "name",
            "healthReg",
            "siteID",
            "datasetID",
            "sampleID",
            "collDT",
            "measure",
            "valavg",
            "reportDate"
        ]
    ]

    latest_obs_df = pd.DataFrame()
    for _, group in all_sites_sub.sort_values("collDT", ascending=False).groupby(
        ["siteID", "measure"]
    ):
        # if only one observation, set second to null
        if len(group) < 2:
            new_row = group.iloc[0].to_frame().T
            new_row.rename(
                columns={
                    "valavg": "valavg_latest",
                    "collDT": "collDT_latest",
                    "sampleID": "sampleID_latest",
                    "reportDate": "reportDate_latest"
                },
                inplace=True,
            )
            new_row["valavg_previous"] = None
            new_row["collDT_previous"] = None
            new_row["sampleID_previous"] = None
            new_row["reportDate_previous"] = None
        else:
            first_obs = group.iloc[0].to_frame().T
            second_obs = group.iloc[1].to_frame().T
            new_row = first_obs.merge(
                second_obs,
                on=["name", "healthReg", "siteID", "datasetID", "measure"],
                suffixes=("_latest", "_previous"),
            )

        new_row = new_row[
            [
                "name",
                "healthReg",
                "siteID",
                "datasetID",
                "measure",
                "valavg_previous",
                "valavg_latest",
                "collDT_previous",
                "collDT_latest",
                "reportDate_previous",
                "reportDate_latest",
                "sampleID_previous",
                "sampleID_latest",
            ]
        ]
        new_row.columns = [
            "name",
            "healthReg",
            "siteID",
            "datasetID",
            "measure",
            "previousObs",
            "latestObs",
            "previousObsDT",
            "latestObsDT",
            "previousReportDT",
            "latestReportDT",
            "sampleID_previous",
            "sampleID_latest",
        ]
        latest_obs_df = pd.concat([latest_obs_df, new_row])
    return latest_obs_df


def app():
    if "df_latest_obs" not in st.session_state:
        time_now = int(time.time())
        # check if a cached latest_obs exists
        if (
            os.path.isfile("./latest_obs.csv")
            and (time_now - os.path.getmtime("./latest_obs.csv"))
            < 86400  # 86400 sec == 24 hours
        ):
            print("Data Cached")
            st.session_state.df_latest_obs = pd.read_csv(
                "./latest_obs.csv", encoding=ENCODING_ALL_SITES, dtype="string"
            )
        else:
            all_sites = download_df(
                BLOB_SERVICE_CLIENT,
                DOWNLOAD_CONTAINER_PATH,
                DOWNLOAD_BLOB_FILENAME,
                ENCODINGS,
            )
            st.session_state.df_latest_obs = get_latest_obs_df(all_sites)
            st.session_state.df_latest_obs.to_csv(
                "./latest_obs.csv", encoding=ENCODING_ALL_SITES, index=False
            )

    # Filter the dataframe based on site names
    sites = st.session_state.df_latest_obs["name"].unique()
    sites = ["All Sites"] + list(sites)
    selected_sites = st.multiselect(
        "Select sites to filter by:", sites, default=["All Sites"]
    )

    # Filter the dataframe based on the selected measures
    measures = st.session_state.df_latest_obs["measure"].unique()
    selected_measures = st.multiselect(
        "Select measures to filter by:", measures, default=measures
    )

    # Filter the dataframe based on the selected measures and sites
    if "All Sites" in selected_sites:
        filtered_df = st.session_state.df_latest_obs[
            st.session_state.df_latest_obs["measure"].isin(selected_measures)
        ]
    else:
        filtered_df = st.session_state.df_latest_obs[
            st.session_state.df_latest_obs["measure"].isin(selected_measures)
            & st.session_state.df_latest_obs["name"].isin(selected_sites)
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
            "fraction": None,
        },
    )

    st.markdown(
    """
    ## Glossary
    | Column            | Description                                               |
    |-------------------|-----------------------------------------------------------|
    | `name`            | The site name.                                            |
    | `healthReg`       | The health region.                                        |
    | `siteID`          | The site ID.                                              |
    | `datasetID`       | The dataset ID.                                           |
    | `measure`         | The measure name.                                         |
    | `fraction`        | `liq` or `sol`                                            |
    | `previousObs`     | The measure value that was observed before `latestObs`.   |
    | `latestObs`       | The measure value that was last recorded.                 |
    | `latestObsDT`     | The date at which `latestObs` was observed.               |
    | `previousReportDT`| The date at which the `previousObs` was reported.         |
    | `latestReportDT`  | The date at which the `latestObs` was reported.           |
    | `previousObsDT`   | The date at which the `previousObs` was observed.         |
    | `sampleID_previous` | The sample ID of the previous observation.              |
    | `sampleID_latest` | The sample ID of the latest observation.                  |
    """
)


st.set_page_config(
    page_title="Latest Measures",
    page_icon="🆕",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🆕 Latest Measures")
print("app re-render")
app()
