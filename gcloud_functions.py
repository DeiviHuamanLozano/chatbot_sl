from google.cloud import storage
from google.oauth2 import service_account
import os

CREDENTIALS = service_account.Credentials.from_service_account_file(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))

def download_blob(bucket_name: str, blob_path: str, file_path: str = "") -> str:
    if file_path == "":
        file_path = blob_path.split("/")[-1]
    
    storage_client = storage.Client(credentials=CREDENTIALS)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    
    blob.download_to_filename(file_path)

    print(f"Blob {blob_path} downloaded to {blob_path}.")
    return file_path


def upload_file_to_blob(bucket_name: str, source_file: str, destination_blob_name: str) -> str:
    storage_client = storage.Client(credentials=CREDENTIALS)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"
    print(f"File {source_file} uploaded to {destination_blob_name}. Public URL: {public_url}")
    return public_url


def list_bucket_folder(bucket_name: str, folder_path: str):
    storage_client = storage.Client(credentials=CREDENTIALS)
    bucket = storage_client.bucket(bucket_name)

    blobs = bucket.list_blobs(prefix=folder_path)

    for blob in blobs:
        print(blob.name)