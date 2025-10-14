install:
    mkdir -p ~/.local/bin
    rm -f ~/.local/bin/sync-llm-logs
    ln -s `pwd`/sqlite-utils/sync-llm-logs.fish ~/.local/bin/sync-llm-logs

    rm -f ~/.local/bin/export-vikunja-tasks*
    ln -s `pwd`/vikunja-export/main.py ~/.local/bin/export-vikunja-tasks

    rm -f ~/.local/bin/sync-satisfactory*
    ln -s `pwd`/satisfactory-sync/main.py ~/.local/bin/sync-satisfactory

    rm -f ~/.local/bin/parse-yt-links*
    ln -s `pwd`/parse-yt-links/parse-yt-links.py ~/.local/bin/parse-yt-links

    rm -f ~/.local/bin/get-container-tags*
    ln -s `pwd`/docker-utils/get_container_tags.py ~/.local/bin/get-container-tags

    rm -f ~/.local/bin/get-openrouter-creds*
    ln -s `pwd`/get-openrouter-creds.py ~/.local/bin/get-openrouter-creds

    rm -f ~/.local/bin/export-gh-comments*
    ln -s `pwd`/github-utils/export_gh_comments.py ~/.local/bin/export-gh-comments
