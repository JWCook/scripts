"""Basic wrappers for some Satisfactory API endpoints"""

import time

from requests import RequestException, Response, Session

from .config import CONFIG

SESSION = Session()


def api_request(function: str, data: str | dict = None, token: str = None) -> Response:
    """Make an (optionally authenticated) API request"""
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    payload = {'function': function}
    if data:
        payload['data'] = data

    response = SESSION.post(
        CONFIG.api_url,
        headers=headers,
        json=payload,
        verify=False,
    )
    response.raise_for_status()
    return response


def get_token() -> str:
    response = api_request(
        'PasswordLogin',
        {'Password': CONFIG.satisfactory_password, 'MinimumPrivilegeLevel': 'Administrator'},
    )
    return response.json()['data']['authenticationToken']


def save(token: str, save_name: str = CONFIG.save_name) -> Response:
    return api_request('SaveGame', {'SaveName': save_name}, token)


def get_save(token: str, save_name: str = CONFIG.save_name) -> bytes:
    """Get latest save contents"""
    save(token, save_name)
    response = api_request('DownloadSaveGame', {'SaveName': save_name}, token)
    return response.content


def health_check() -> bool:
    try:
        response = api_request('HealthCheck', {'ClientCustomData': ''})
        return response.json()['data']['health'] == 'healthy'
    except (RequestException, KeyError):
        return False


def get_state(token: str) -> dict:
    response = api_request('QueryServerState', token=token)
    return response.json()['data']['serverGameState']


def restart(token: str):
    """Shut down the server process and let the service manager restart it"""
    api_request('Shutdown', token=token)


def test_save_restart(token: str):
    """Save and cleanly restart the server"""
    save(token=token)
    time.sleep(15)  # TODO: Way to check that the save is complete instead of sleep?
    restart(token=token)


if __name__ == '__main__':
    test_save_restart()
