"""Utilities to interact with a remote Nextcloud server via WebDAV API.

Note: If needed, this could be easily adapted to work with any WebDAV server.
"""

from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from pathlib import Path
from xml.etree import ElementTree

from dateutil.parser import parse as parse_date

from .config import CONFIG, NC_SESSION

logger = getLogger(__name__)


@dataclass
class RemoteFile:
    id: int
    path: str
    filename: str
    mtime: datetime

    @classmethod
    def from_xml(cls, element) -> 'RemoteFile':
        path = element.find('.//{DAV:}href').text
        return cls(
            id=int(path.split('_')[0]),
            path=path,
            filename=path.split('/')[-1],
            mtime=parse_date(element.find('.//{DAV:}getlastmodified').text),
        )


def webdav_ls() -> list[RemoteFile]:
    """List all files in the remote directory"""
    response = NC_SESSION.request('PROPFIND', CONFIG.nc_base_url, headers={'Depth': '1'})
    xml_response = ElementTree.fromstring(response.content).findall('{DAV:}response')
    return [RemoteFile.from_xml(element) for element in xml_response if not _is_dir(element)]


def _is_dir(element) -> bool:
    return element.find('.//{DAV:}collection') is not None


def webdav_upload(local_path: Path, remote_path: Path):
    """Upload files to Nextcloud via WebDAV"""
    _webdav_mkdir()
    response = NC_SESSION.put(
        f'{CONFIG.nc_base_url}/{remote_path}',
        data=local_path.read_bytes(),
    )

    if response.ok:
        logger.debug(f'Uploaded {local_path} -> {CONFIG.nc_base_url}/{remote_path}')
    else:
        logger.error(f'Error uploading {local_path}: {response.status_code} {response.text}')


def webdav_rename(src_path, dest_path):
    """Rename a file on the remote server"""
    response = NC_SESSION.request(
        'MOVE',
        f'{CONFIG.nc_base_url}/{src_path}',
        headers={'Destination': f'{CONFIG.nc_base_url}/{dest_path}'},
    )
    if response.status_code == 201:
        logger.debug(f'Renamed {src_path} -> {dest_path}')
    else:
        logger.error(f'Error renaming {src_path}: {response.status_code} {response.text}')


def webdav_delete(remote_path):
    """Delete a file on the remote server"""
    response = NC_SESSION.delete(f'{CONFIG.nc_base_url}/{remote_path}')
    if response.status_code == 204:
        logger.debug(f'Deleted {remote_path}')
    else:
        logger.error(f'Error deleting {remote_path}: {response.status_code} {response.text}')


def _webdav_mkdir():
    """Create the remote folder if it doesn't already exist"""
    response = NC_SESSION.request('MKCOL', CONFIG.nc_base_url)
    if response.status_code == 201:
        logger.debug(f'Folder {CONFIG.nc_dir} created')
    elif response.status_code == 405:
        logger.debug(f'Folder {CONFIG.nc_dir} already exists')
    else:
        logger.error(f'Error creating {CONFIG.nc_dir}: {response.status_code} {response.text}')
