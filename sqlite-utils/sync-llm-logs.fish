#!/usr/bin/env fish
# Sync prompt logs from llm CLI

function deets -a path
    set mtime (stat -c "%y" $path | cut -d. -f1)
    echo "$mtime $(/bin/du -h $path)"
end

function list-cols -a db_path -a table
    sqlite3 $db_path  "PRAGMA table_info($table)" | awk -F '|' '{print $2}' | paste -sd,
end

function merge-table -a table -a dest_db -a src_db
    set cols (list-cols $dest_db $table)
    sqlite3 $dest_db "\
        ATTACH DATABASE '$(realpath $src_db)' AS src_db; \
        REPLACE INTO $table ($cols) \
            SELECT * FROM (SELECT * FROM src_db.$table);"
end

function llm-sync-logs
    set local_db ~/.config/io.datasette.llm/logs.db
    set remote_db ~/Nextcloud/Data/llm-logs.db
    set bak_db {$local_db}.bak
    set count_query "SELECT COUNT(*) FROM responses"
    set row_count_local (sqlite3 $local_db "$count_query")
    set row_count_remote (sqlite3 $remote_db "$count_query")

    echo -e "Syncing:\n  ⬆️ $(deets $local_db)\n  ⬇️ $(deets $remote_db)"
    cp $local_db $bak_db
    merge-table conversations $local_db $remote_db
    merge-table responses $local_db $remote_db
    if test $status -ne 0
        echo "❌ Sync failed; backup saved at $bak_db"
        return 1
    end

    cp $local_db $remote_db
    rm $bak_db

    set row_count_synced (sqlite3 $local_db "$count_query")
    set n_rows_local (math $row_count_synced - $row_count_local)
    set n_rows_remote (math $row_count_synced - $row_count_remote)
    echo "✅ Sync complete. Added $n_rows_local rows to local db and $n_rows_remote rows to remote db."
end

llm-sync-logs
# llm logs list -n 0 > llm-logs.md
