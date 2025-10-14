#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "dotenv",
#     "environ-config",
#     "minio",
#     "requests",
# ]
# ///
from logging import getLogger

from api import SatisfactoryAPIClient
from config import CONFIG
from storage import StorageClient

# Amount of time in seconds to allow for local/remote timestamps to differ before re-uploading,
#  e.g., due to previous upload/download time. Not attempting to make this a precise real-time sync.
MIN_REUPLOAD_INTERVAL = 30

logger = getLogger(__name__)


# WIP
def sync_save():
    """Get latest save contents from the Satisfactory server and upload to remote storage"""
    api_client = SatisfactoryAPIClient()
    storage_client = StorageClient()
    if CONFIG.dry_run:
        logger.warning('Dry run enabled')

    # Get local and remote timestamps (both should be UTC datetime objects)
    last_saved_local = api_client.get_last_modified()
    last_saved_remote = storage_client.stat_save()._last_modified
    local_icon = '🌟' if last_saved_local >= last_saved_remote else ''
    remote_icon = '🌟' if last_saved_local < last_saved_remote else ''
    logger.info(
        f'Changes fetched.\nLocal save last modified:  {last_saved_local} {local_icon}\n'
        + f'Remote save last modified: {last_saved_remote} {remote_icon}'
    )

    # Skip if the saves are already synced... ish
    diff_seconds = abs((last_saved_local - last_saved_remote).total_seconds())
    if diff_seconds < MIN_REUPLOAD_INTERVAL:
        logger.info(f'🟰 Save files already synced ({diff_seconds} seconds apart)')

    # Upload local save to remote storage if local is newer
    elif last_saved_local > last_saved_remote:
        if not CONFIG.dry_run:
            save_content = api_client.get_save()
            storage_client.upload_save(save_content)
        logger.info('⬆️ Uploaded save file to remote storage')

    # Download remote save to local storage if remote is newer
    # TODO: Set as local autoload save
    else:
        if not CONFIG.dry_run:
            save_content = storage_client.download_save()
            api_client.upload_save(save_content)
        logger.info('⬇️ Downloaded save file from remote storage')


if __name__ == '__main__':
    sync_save()
