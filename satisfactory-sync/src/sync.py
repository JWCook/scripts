from .api import get_save, get_token
from .storage import get_client, upload_save


# WIP
def backup_save():
    """Get latest save contents from the Satisfactory server and upload to remote storage"""
    token = get_token()
    save_content = get_save(token)

    client = get_client()
    upload_save(client, save_content)


if __name__ == '__main__':
    backup_save()
