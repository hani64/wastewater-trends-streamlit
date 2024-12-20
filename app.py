import os
import streamlit as st
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import pandas as pd


load_dotenv()
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
ACCOUNT_URL = os.getenv("ACCOUNT_URL")
CLIENT_ID = os.getenv("CLIENT_ID")

DOWNLOAD_BLOB_FILENAME = "wastewater-trend-out.csv"
UPLOAD_BLOB_FILENAME = "wastewater-trend-out.csv"

blob_service_client = BlobServiceClient.from_connection_string(
    conn_str=AZURE_BLOB_CONNECTION_STRING
)
# blob_service_client = BlobServiceClient(
#     ACCOUNT_URL, 
#     credential=ManagedIdentityCredential(client_id=CLIENT_ID)
# )

def download_wastewater_trends():
    blob_client = blob_service_client.get_blob_client(
        container="hani", blob=DOWNLOAD_BLOB_FILENAME
    )
    with open(f"./{DOWNLOAD_BLOB_FILENAME}", "wb") as blob:
        blob_data = blob_client.download_blob()
        blob_data.readinto(blob)
    print("Data Downloaded")


def upload_wastewater_trends(df: pd.DataFrame):
    blob_client = blob_service_client.get_blob_client(
        container="hani", blob=UPLOAD_BLOB_FILENAME
    )
    df.to_csv(f"./{UPLOAD_BLOB_FILENAME}", encoding="utf-16be", index=False)
    with open(f"./{UPLOAD_BLOB_FILENAME}", "rb") as blob:
        blob_client.upload_blob(data=blob, overwrite=True)
    print("Data Uploaded")


@st.dialog("Change Row Data")
def edit_data_form(selected_index, csv=f"./{DOWNLOAD_BLOB_FILENAME}"):
    edited_df = st.data_editor(
        st.session_state.df.iloc[[selected_index]],
        column_order=[
            "Location", "measure", 
            "latestTrends", "LatestLevel", 
            "Grouping", "City", "Province", 
            "Viral_Activity_Level"
        ],
        column_config={
            "Viral_Activity_Level": st.column_config.SelectboxColumn(
                "Viral_Activity_Level",
                options=[
                    "High",
                    "Moderate",
                    "Low",
                    "Non-detect",
                    "NA2"
                ],
                required=True,
            )
        },
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Submit", type="primary"):
        # re-download most up-to-date csv before editing and uploading
        download_wastewater_trends()
        st.session_state.df = pd.read_csv(csv, encoding="utf-16be", dtype="string")

        # gotta make this more efficient later
        #st.session_state.df.loc[selected_index] = edited_df
        st.session_state.df.loc[selected_index, "Location"] = edited_df.loc[selected_index, "Location"]
        st.session_state.df.loc[selected_index, "measure"] = edited_df.loc[selected_index, "measure"]
        st.session_state.df.loc[selected_index, "latestTrends"] = edited_df.loc[selected_index, "latestTrends"]
        st.session_state.df.loc[selected_index, "LatestLevel"] = edited_df.loc[selected_index, "LatestLevel"]
        st.session_state.df.loc[selected_index, "Grouping"] = edited_df.loc[selected_index, "Grouping"]
        st.session_state.df.loc[selected_index, "City"] = edited_df.loc[selected_index, "City"]
        st.session_state.df.loc[selected_index, "Province"] = edited_df.loc[selected_index, "Province"]
        st.session_state.df.loc[selected_index, "Viral_Activity_Level"] = edited_df.loc[selected_index, "Viral_Activity_Level"]

        upload_wastewater_trends(st.session_state.df)

        print("dialog triggered re-render")
        st.rerun()


def app():
    if "df" not in st.session_state:
        download_wastewater_trends()
        st.session_state.df = pd.read_csv(
            DOWNLOAD_BLOB_FILENAME, 
            encoding="utf-16be", 
            dtype="string",
        )

    # Create a dataframe where only a single-row is selectable
    selected_row = st.dataframe(
        st.session_state.df,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True,
        column_order=[
            "Location", "measure", 
            "latestTrends", "LatestLevel", 
            "Grouping", "City", "Province", 
            "Viral_Activity_Level"
        ]
    )

    # Get the index of the selected row, iff a row is selected
    if selected_row.selection.get("rows", []):
        edit_data_form(selected_row.selection.rows[0])


st.set_page_config(
    page_title="Infobase Table",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# hack to make the dialog box wider
st.markdown('''<style>
div[data-testid="stDialog"] div[role="dialog"] {
    width: 80%;
}
</style>''', unsafe_allow_html=True)

st.title("📈 Wastewater Trends")
print("app re-render")
app()
st.markdown("""
## How to Use This App

1. Use the selection box on the left of any row to select the site you want to modify
2. The selected row will be highlighted to show it is active
3. Click on any field value in the "Change Row Data" dialog to modify it
5. Click "Submit" to save your changes

For any questions or issues, please contact the system administrator.
""")
