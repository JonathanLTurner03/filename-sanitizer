# File Transfer TUI

A lightweight Python script that copies or moves files from one folder to another, automatically renaming any filenames that aren’t valid on the destination filesystem. It displays a live progress bar showing files and bytes transferred.

## Features

* Prompt for **source** and **destination** folders.
* Choose source/destination **filesystem types** (FAT32, exFAT, NTFS, ext4, HFS+).
* Automatically replace invalid characters in filenames with `_`.
* Option to **COPY** (duplicates files) or **MOVE** (relocates files; if source is read-only, it forces COPY).
* Scans source folder to count total files and bytes, then transfers them one by one.
* Shows live progress: percentage, transfer speed, ETA, and file-count status.

## Requirements

* Python 3.7+
* prompt\_toolkit
* rich

Install dependencies:

```
# (Optional) : Create a virtual environment
python -m venv .venv 

# Install Dependencies from the Requirements file.
pip install -r requirements.txt
```

## Usage

1. Save the script as `filename-sanitizer.py`.
2. Run:

   ```
   python filename-sanitizer.py
   ```
3. Follow prompts:

   1. **Enter source folder path** (must exist).
   2. **Select SOURCE filesystem** (affects allowed characters).
   3. **Enter destination folder path** (it will be created if missing).
   4. **Select DESTINATION filesystem** (used for filename sanitization).
   5. **Choose OPERATION**: `COPY` or `MOVE`.
   6. **Confirm** after the script reports total files and size.

The script will then transfer each file, renaming invalid filenames on the fly (e.g., `a:b.txt` → `a_b.txt`), and display a progress bar until completion.

## Supported Filesystems

* **FAT32 / exFAT / NTFS**: disallow `< > : " / \ | ? *`
* **ext4**: disallows `/` and null (`\0`)
* **HFS+**: disallows `:`

You can modify or add to the `FILESYSTEMS` dictionary in the script if needed. (Will be adding more eventually)

## License

```
            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
                    Version 2, December 2004

 Copyright (C) 2025 Jonathan Turner <turner@atlantissrv.com>

 Everyone is permitted to copy and distribute verbatim or modified
 copies of this license document, and changing it is allowed as long
 as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.
```
