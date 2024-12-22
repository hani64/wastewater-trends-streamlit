import os
import streamlit as st
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import pandas as pd
import plotly.express as px


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
        (df['Grouping'] == 'Site') &
        # Then exclude locations that also have City records
        ~df['City'].isin(
            df[df['Grouping'] == 'City']['Location'].unique()
        )
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
        "Yukon": "YT"
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
            

    data = {
        "labels": labels,
        "parents": parents,
        "values": values
    }

    # Convert to a DataFrame
    data = pd.DataFrame(data)

    fig = px.sunburst(
        data,
        names='labels',
        parents='parents',
        color='values',
        hover_data=['values'],
        color_discrete_map={'NA2': '#ADD8E6', 'Non-detect': '#ADD8E6', 'Low': '#90EE90', 'Moderate': '#FFD700', 'High': '#FF6B6B'},
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

    if "measure" not in st.session_state:
        st.session_state.measure = 'covN2'

    left, right = st.columns([4, 1], vertical_alignment='center')
    left.plotly_chart(create_sunburst_graph(st.session_state.df, st.session_state.measure), use_container_width=True)
    if right.button("covN2", use_container_width=True):
        st.session_state.measure = 'covN2'
        st.rerun()
    if right.button("rsv", use_container_width=True):
        st.session_state.measure = 'rsv'
        st.rerun()
    if right.button("fluA", use_container_width=True):
        st.session_state.measure = 'fluA'
        st.rerun()
    if right.button("fluB", use_container_width=True):
        st.session_state.measure = 'fluB'
        st.rerun()

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
