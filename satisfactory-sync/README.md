# Satisfactory sync

Script to sync Satisfactory saves between a multiplayer server and remote object storage.
Does not need to run on the same machine as the Satistactory server.

# Usage
* Add a `.env` file or set environment variables; see [`.env_sample`](.env_sample)
* `./main.py`


# TODO
Bidirectional sync:
* If remote is newer, download, and send to server via API
  * May require a server restart?
  * Make sure configured save name matches Satisfactory server's `autoLoadSessionName`

Automated sync:
* Watch for changes in real time?
* Or just schedule periodic syncs?
