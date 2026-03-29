from google.cloud import storage
import os
import uuid

BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

def upload_file(file_path):
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

        filename = file_path.split("/")[-1]
        unique_name = f"{uuid.uuid4()}-{filename}"

        blob = bucket.blob(unique_name)

        blob.upload_from_filename(file_path, content_type="image/jpeg")

        blob.make_public()

        return blob.public_url

    except Exception as e:
        print(f"GCS Upload Error: {e}")
        raise