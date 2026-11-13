# Privacy Policy — ResumeWriter Launcher

_Last updated: 2026-11-14_

The ResumeWriter Launcher ("the Launcher") is a small desktop app that installs, runs, updates
and uninstalls the ResumeWriter application on your computer. This policy explains what the
Launcher does with your data. In short: **the Launcher does not collect, transmit or sell your
personal data, and it contains no analytics or telemetry.**

## What the Launcher stores on your computer
Everything is stored locally, in a folder owned by your user account:

| OS | Location |
|---|---|
| Windows | `%LOCALAPPDATA%\ResumeWriter` |
| macOS | `~/Library/Application Support/ResumeWriter` |
| Linux | `~/.local/share/ResumeWriter` |

It contains:
- the installed ResumeWriter application files and its Python virtual environment;
- `state.json` (whether ResumeWriter is installed, where, and the installed version);
- log files (`logs/`) with the output of install, update, server and GUI commands.

Your configuration (the `.env` file) is created and edited through the Launcher's Settings screen
and is stored only in the installation folder on your computer. The Launcher never uploads or
shares its contents.

Uninstall removes the installation folder (including your `.env`). To remove the rest (`state.json`
and logs), delete the folder listed above.

## Network connections the Launcher makes
Only when you click Install or Update, the Launcher connects to:
- **GitHub** (`github.com`) over HTTPS, to download or update the ResumeWriter source code; and
- **the Python Package Index** (`pypi.org` and its file hosts), through `pip`, to download the
  application's dependencies.

These services receive standard connection information (such as your IP address) as with any web
request, and are governed by their own privacy policies. The Launcher sends no personal data
to them and no data to the Launcher's authors.

The Launcher also checks `127.0.0.1` (your own machine) to see whether the local ResumeWriter
server is running.

## The ResumeWriter application
The Launcher starts the ResumeWriter server and GUI on your computer. What those programs do with
your data (for example, any database or service configured in your `.env`) is determined by
ResumeWriter and your own configuration, not by the Launcher, and is outside the scope of this
policy. Please refer to the ResumeWriter project's own documentation.

## Logs
Log files may contain file paths and error messages from the commands the Launcher runs. They
stay on your computer and are never sent anywhere. You can view them from the Launcher
("Show logs" / "Open log file") and delete them at any time.

## Children
The Launcher is not directed at children and does not knowingly collect any personal information.

## Changes
If this policy changes, the updated version will be published in this repository with a new
"Last updated" date.

## Contact
Questions about this policy: **<add contact email or repository issues URL here>**
