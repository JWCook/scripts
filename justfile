install:
    mkdir -p ~/.local/bin
    rm -f ~/.local/bin/sync-llm-logs
    ln -s `pwd`/sqlite-utils/sync-llm-logs.fish ~/.local/bin/sync-llm-logs
    rm -f ~/.local/bin/vk-export.py
    ln -s `pwd`/vikunja-export/main.py ~/.local/bin/vk-export.py
    rm -f ~/.local/bin/sync-satisfactory.py
    ln -s `pwd`/satisfactory-sync/main.py ~/.local/bin/sync-satisfactory.py
    rm -rf ~/.local/bin/parse-yt-links.py
    ln -s `pwd`/parse-yt-links/parse-yt-links.py ~/.local/bin/parse-yt-links.py
    rm -rf ~/.local/bin/get-container-tags.py
    ln -s `pwd`/docker-utils/get_container_tags.py ~/.local/bin/get-container-tags.py
    rm -rf ~/.local/bin/get-openrouter-creds.py
    ln -s `pwd`/get-openrouter-creds.py ~/.local/bin/get-openrouter-creds.py
