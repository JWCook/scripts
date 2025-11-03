# Vikunja Task Export

This is a tool to export relevant text from tasks in [Vikunja](https://vikunja.io) to Markdown files,
which are then uploaded to Nextcloud. File upload is done directly via WebDAV API, allowing it to be
run headlessly, i.e. without relying on the desktop sync client.

This is very much tailored to my own needs, but it could be made more generic if there's interest.

My use case for this is taking useful notes I've previously added to tasks, and exporting them
to make them easily searchable using command line tools like `ripgrep`.

## Usage
Install [`uv`](https://docs.astral.sh/uv):
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Set Vikunja and Nextcloud connection info in either environment variables or a [`.env`](.env.sample) file:
```sh
export VK_HOST=vikunja.example.com
export VK_TOKEN=your-api-token
export NC_USER=test.user
export NC_PASS=nc-app-password
export NC_HOST=nextcloud.example.com
export NC_DIR=test
```

Run the script:
```sh
./main.py
```

Optionally symlink `main.py` to somewhere on your `$PATH`. All python-specific setup us handled by `uv`.

## Output format
**Summary:**
A condensed summary of all tasks will be written to one file, in the format:
```
1✅ : Inbox / test post, please ignore 2025-01-18
2✅ : Software / Evaluate task management tools [📖research] 2025-01-21
3   : Household / Replace HVAC air filter 2025-02-02
5   : Software / Make script to dump task text [📖research] 2025-02-04
```

**Details:**
Any tasks with a description and/or comments will have their contents converted to separate
Markdown files, in the format:
```md
# Make script to dump task text
* URL: https://try.vikunja.io/tasks/15
* Created: 2025-02-04
* Updated: 2025-02-10
* Project: Software
* Labels: 📖research

# Description
This is mainly for the purpose of making my notes in Vikunja easily searchable
alongside my main Markdown notes.

# Comments

## Jordan Cook 2025-02-04
Options to try out:
* CLI tool: [vja](https://github.com/cernst72/vja)
* API: [GET /tasks/all](https://try.vikunja.io/api/v1/docs#tag/task/paths/~1tasks~1all/get)

## Jordan Cook 2025-02-06
Text fields are in HTML format. Looked through several options to convert back to Markdown.
This one looks promising: [html2text](https://github.com/Alir3z4/html2text)
```
