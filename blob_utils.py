import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import pandas as pd


load_dotenv()
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
ACCOUNT_URL = os.getenv("ACCOUNT_URL")
CLIENT_ID = os.getenv("CLIENT_ID")

# ENCODINGS = ["utf-8", "utf-16be", "latin1"]


def get_blob_service_client_from_conn_str():
    return BlobServiceClient.from_connection_string(
        conn_str=AZURE_BLOB_CONNECTION_STRING
    )


def get_blob_service_client_from_cred():
    return BlobServiceClient(
        ACCOUNT_URL, credential=ManagedIdentityCredential(client_id=CLIENT_ID)
    )


def download_df(blob_service_client, container_path, blob_filename, encodings):
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
    blob_service_client, df: pd.DataFrame, container_path, blob_filename, encodings
):
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
