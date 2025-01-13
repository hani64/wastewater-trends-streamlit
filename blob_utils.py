import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.identity import ManagedIdentityCredential
import pandas as pd
import streamlit as st
import json
from datetime import datetime


load_dotenv()
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
ACCOUNT_URL = os.getenv("ACCOUNT_URL")
CLIENT_ID = os.getenv("CLIENT_ID")

# ENCODINGS = ["utf-8", "utf-16be", "latin1"]


def get_blob_service_client_from_conn_str() -> BlobServiceClient:
    return BlobServiceClient.from_connection_string(
        conn_str=AZURE_BLOB_CONNECTION_STRING
    )


def get_blob_service_client_from_cred() -> BlobServiceClient:
    return BlobServiceClient(
        ACCOUNT_URL, credential=ManagedIdentityCredential(client_id=CLIENT_ID)
    )


def download_df(
    blob_service_client: BlobServiceClient,
    container_path: str,
    blob_filename: str,
    encodings: list[str],
) -> None:
    blob_client = blob_service_client.get_blob_client(
        container=container_path, blob=blob_filename
    )
    with open(f"./{blob_filename}", "wb") as blob:
        blob_data = blob_client.download_blob()
        blob_data.readinto(blob)
    print("Data Downloaded")

    df = None
    for encoding in encodings:
        try:
            df = pd.read_csv(f"./{blob_filename}", encoding=encoding, dtype="string")
            print(f"Data read successfully with encoding: {encoding}")
            return df
        except Exception as e:
            continue

    if df is None:
        raise ValueError("Failed to read data with all provided encodings.")
    return df


def upload_df(
    blob_service_client: BlobServiceClient,
    df: pd.DataFrame,
    container_path: str,
    blob_filename: str,
    encodings: list[str],
) -> None:
    for encoding in encodings:
        try:
            df.to_csv(f"./{blob_filename}", encoding=encoding, index=False)
            with open(f"./{blob_filename}", "rb") as blob:
                blob_client = blob_service_client.get_blob_client(
                    container=container_path, blob=blob_filename
                )
                blob_client.upload_blob(data=blob, overwrite=True)
            print(f"Data uploaded successfully with encoding: {encoding}")
            return
        except Exception as e:
            continue

    raise ValueError("Failed to upload data with all provided encodings.")


def get_user_info() -> dict:
    user_info_json = st.context.headers.get("Rstudio-Connect-Credentials")
    if user_info_json is None:
        return None
    return json.loads(user_info_json)


def get_username() -> str:
    user_info = get_user_info()
    if user_info is None:
        return "anon"
    return user_info.get("user")


def get_log_entry(
    username: str, old_data: pd.DataFrame, new_data: pd.DataFrame, page: str
) -> pd.DataFrame:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Find the changes
    changes = {
        col: {"old": old_data[col], "new": new_data[col]}
        for col in old_data.index
        if old_data[col] != new_data[col]
    }

    log_entry = {
        "User": username,
        "Time": current_time,
        "Page": page,
        "Location": old_data.get("Location", "N/A"),
        "Measure": old_data.get("measure", "N/A"),
        "Changes": changes,
    }

    # return log entry
    print(log_entry)
    print(get_user_info())
    return pd.DataFrame([log_entry])
