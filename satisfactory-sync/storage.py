from datetime import datetime
from tempfile import NamedTemporaryFile

from config import CONFIG
from minio import Minio


class StorageClient:
    """Wrapper class for some basic S3(-compatible) operations"""

    def __init__(self):
        self.client = Minio(
            CONFIG.sync_endpoint,
            access_key=CONFIG.aws_access_key,
            secret_key=CONFIG.aws_secret_key,
            secure=True,
        )

    def upload_save(self, save_content: bytes):
        """Upload save file contents to an S3-compatible bucket"""

        # Assume we fetched save contents via the API; save to a temp file because minio doesn't
        # support file-like objects / streaming uploads
        with NamedTemporaryFile(delete=True) as temp_file:
            temp_file.write(save_content)
            self.client.fput_object(
                CONFIG.sync_bucket,
                f'{CONFIG.save_name}.sav',
                temp_file.name,
            )

    def download_save(self) -> bytes:
        """Download the remote save file"""
        with NamedTemporaryFile(delete=False) as temp_file:
            self.client.fget_object(
                CONFIG.sync_bucket, f'{CONFIG.save_name}.sav', tmp_file_path=temp_file.name
            )
            return temp_file.read()

    def get_last_modified(self) -> datetime:
        """Get the last modified timestamp of the save file in the S3-compatible bucket"""
        return self.stat_save()._last_modified

    def stat_save(self):
        """Get the last modified timestamp of the save file in the S3-compatible bucket"""
        return self.client.stat_object(CONFIG.sync_bucket, f'{CONFIG.save_name}.sav')
