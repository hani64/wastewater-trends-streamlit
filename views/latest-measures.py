import os
import pandas as pd
from dotenv import load_dotenv
import streamlit as st
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import time


load_dotenv()
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
ACCOUNT_URL = os.getenv("ACCOUNT_URL")
CLIENT_ID = os.getenv("CLIENT_ID")

DOWNLOAD_BLOB_FILENAME = "allSites_Updated.csv"

DOWNLOAD_CONTAINER_PATH = "hani"

ENCODING_ALL_SITES = os.getenv("ENCODING_ALL_SITES", default="utf-8")


blob_service_client = BlobServiceClient.from_connection_string(
    conn_str=AZURE_BLOB_CONNECTION_STRING
)
# blob_service_client = BlobServiceClient(
#     ACCOUNT_URL,
#     credential=ManagedIdentityCredential(client_id=CLIENT_ID)
# )


def download_all_sites():
    time_now = int(time.time())
    if os.path.isfile(f"./{DOWNLOAD_BLOB_FILENAME}") and os.path.getmtime(
        f"./{DOWNLOAD_BLOB_FILENAME}"
    ) > (time_now - 86400):
        print("Data Cached")
        return
    blob_client = blob_service_client.get_blob_client(
        container=DOWNLOAD_CONTAINER_PATH, blob=DOWNLOAD_BLOB_FILENAME
    )
    with open(f"./{DOWNLOAD_BLOB_FILENAME}", "wb") as blob:
        blob_data = blob_client.download_blob()
        blob_data.readinto(blob)
    print("Data Downloaded")


def get_latest_obs_df(all_sites):
    # convert collDT to datetime
    all_sites["collDT"] = pd.to_datetime(all_sites["collDT"])
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
            "fraction",
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
                },
                inplace=True,
            )
            new_row["valavg_previous"] = None
            new_row["collDT_previous"] = None
            new_row["sampleID_previous"] = None
        else:
            first_obs = group.iloc[0].to_frame().T
            second_obs = group.iloc[1].to_frame().T
            new_row = first_obs.merge(
                second_obs,
                on=["name", "healthReg", "siteID", "datasetID", "measure", "fraction"],
                suffixes=("_latest", "_previous"),
            )

        new_row = new_row[
            [
                "name",
                "healthReg",
                "siteID",
                "datasetID",
                "measure",
                "fraction",
                "valavg_previous",
                "valavg_latest",
                "collDT_previous",
                "collDT_latest",
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
            "fraction",
            "previousObs",
            "latestObs",
            "previousObsDT",
            "latestObsDT",
            "sampleID_previous",
            "sampleID_latest",
        ]
        latest_obs_df = pd.concat([latest_obs_df, new_row])
    return latest_obs_df


def app():
    if "df_latest_obs" not in st.session_state:
        download_all_sites()
        all_sites = pd.read_csv(
            DOWNLOAD_BLOB_FILENAME,
            encoding=ENCODING_ALL_SITES,
            dtype="string",
        )
        st.session_state.df_latest_obs = get_latest_obs_df(all_sites)

    st.dataframe(
        st.session_state.df_latest_obs,
        use_container_width=True,
        hide_index=True,
        column_config={
            "latestObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
            "previousObsDT": st.column_config.DatetimeColumn(
                format="YYYY-MM-DD",
            ),
        },
    )


st.set_page_config(
    page_title="Latest Measures",
    page_icon="🆕",
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

st.title("🆕 Latest Measures")
print("app re-render")
app()
