install:
    mkdir -p ~/.local/bin
    rm -f ~/.local/bin/sync-llm-logs
    ln -s `pwd`/sqlite-utils/sync-llm-logs.fish ~/.local/bin/sync-llm-logs

    rm -f ~/.local/bin/vikunja-export.py ~/.local/bin/export-vikunja-tasks.py
    ln -s `pwd`/vikunja-export/main.py ~/.local/bin/export-vikunja-tasks.py

    rm -f ~/.local/bin/sync-satisfactory.py
    ln -s `pwd`/satisfactory-sync/main.py ~/.local/bin/sync-satisfactory.py

    rm -f ~/.local/bin/parse-yt-links.py
    ln -s `pwd`/parse-yt-links/parse-yt-links.py ~/.local/bin/parse-yt-links.py

    rm -f ~/.local/bin/get-container-tags.py
    ln -s `pwd`/docker-utils/get_container_tags.py ~/.local/bin/get-container-tags.py

    rm -f ~/.local/bin/get-openrouter-creds.py
    ln -s `pwd`/get-openrouter-creds.py ~/.local/bin/get-openrouter-creds.py

    rm -f ~/.local/bin/export-gh-comments.py
    ln -s `pwd`/github-utils/export_gh_comments.py ~/.local/bin/export-gh-comments.py
