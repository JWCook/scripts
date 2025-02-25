from tempfile import NamedTemporaryFile

from config import CONFIG
from minio import Minio


def get_client() -> Minio:
    return Minio(
        CONFIG.sync_endpoint,
        access_key=CONFIG.aws_access_key,
        secret_key=CONFIG.aws_secret_key,
        secure=True,
    )


def upload_save(client: Minio, save_content: bytes):
    """Upload save file contents to an S3-compatible bucket"""

    # Assume we fetched save contents via the API; save to a temp file because minio doesn't
    # support file-like objects / streaming uploads
    with NamedTemporaryFile(delete=True) as temp_file:
        temp_file.write(save_content)
        client.fput_object(
            CONFIG.sync_bucket,
            f'{CONFIG.save_name}.sav',
            temp_file.name,
        )


def download_save(client: Minio) -> bytes:
    """Download the remote save file"""
    with NamedTemporaryFile(delete=False) as temp_file:
        client.fget_object(
            CONFIG.sync_bucket, f'{CONFIG.save_name}.sav', tmp_file_path=temp_file.name
        )
        return temp_file.read()


def stat_save(client: Minio):
    """Get the last modified timestamp of the save file in the S3-compatible bucket"""
    return client.stat_object(CONFIG.sync_bucket, f'{CONFIG.save_name}.sav')
