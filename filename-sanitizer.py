import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Set

# Imports for the TUI (Requires prompt_toolkit and rich packages)
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style

from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
from rich.console import Console


# Map a filesystem name → set of allowed characters
# (For simplicity, we list “disallowed” characters; the code below uses allowed = (all ASCII except disallowed).)
FILESYSTEMS: Dict[str, Set[str]] = {
    "FAT32": set(
        chr(i)
        for i in range(32, 127)  # printable ASCII except control codes
        if chr(i) not in '<>:"/\\|?*'
    ),
    "exFAT": set(
        chr(i)
        for i in range(32, 127)
        if chr(i) not in '<>:"/\\|?*'
    ),
    "NTFS": set(
        chr(i)
        for i in range(32, 127)
        if chr(i) not in '<>:"/\\|?*'
    ),
    "ext4": set(
        chr(i)
        for i in range(1, 127)  # ext4 only disallows "/" and null (chr(0)). We'll exclude "/".
        if chr(i) != "/"
    ),
    "HFS+": set(
        chr(i)
        for i in range(1, 127)
        if chr(i) != ":"
    ),
    # TODO: Check other filesystems as needed, along with double checking current characters.
}


def sanitize_filename(original: str, allowed_chars: Set[str]) -> str:
    """
    Replace any character not in allowed_chars with "_".
    Return the sanitized filename; if unchanged, returns original.
    """
    new_name_chars = []
    changed = False
    for ch in original:
        if ch in allowed_chars:
            new_name_chars.append(ch)
        else:
            new_name_chars.append("_")
            changed = True
    sanitized = "".join(new_name_chars)
    return sanitized


class PathExistsValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        if not text:
            raise ValidationError(message="Path cannot be empty", cursor_position=len(document.text))
        p = Path(text)
        if not p.exists() or not p.is_dir():
            raise ValidationError(message="Directory does not exist", cursor_position=len(document.text))


class PathWritableValidator(Validator):
    def validate(self, document):
        text = document.text.strip()
        if not text:
            raise ValidationError(message="Path cannot be empty", cursor_position=len(document.text))
        p = Path(text)
        # If it exists, check writability. If not, check parent.
        if p.exists():
            if not os.access(str(p), os.W_OK):
                raise ValidationError(message="Directory is not writable", cursor_position=len(document.text))
        else:
            parent = p.parent
            if not parent.exists() or not os.access(str(parent), os.W_OK):
                raise ValidationError(
                    message=f"Cannot create directory here (no write permission in {parent})",
                    cursor_position=len(document.text),
                )


# Main Sentinel Loop
def main():
    console = Console()
    style = Style.from_dict({
        "": "#ff9e00",
        "prompt": "#00ff9e bold",
    })

    console.print("[bold underline]File Transfer TUI Script[/bold underline]\n")

    # Source Folder and Filesystem
    source_path_str = prompt(
        [("class:prompt", "1) Enter source folder path: ")],
        validator=PathExistsValidator(),
        style=style,
    ).strip()
    source_root = Path(source_path_str)

    fs_completer = WordCompleter(list(FILESYSTEMS.keys()), ignore_case=True)
    source_fs = prompt(
        [("class:prompt", "2) Select SOURCE filesystem type (e.g. FAT32, NTFS, ext4): ")],
        completer=fs_completer,
        validator=Validator.from_callable(
            lambda t: t.strip() in FILESYSTEMS,
            error_message="Choose one of: " + ", ".join(FILESYSTEMS.keys()),
            move_cursor_to_end=True,
        ),
        style=style,
    ).strip()
    source_allowed = FILESYSTEMS[source_fs]

    # Destination Folder and Filesystem
    dest_path_str = prompt(
        [("class:prompt", "3) Enter destination folder path (will be created if needed): ")],
        style=style,
    ).strip()
    dest_root = Path(dest_path_str)
    if not dest_root.exists():
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created destination folder: {dest_root}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to create {dest_root}: {e}[/red]")
            sys.exit(1)

    dest_fs = prompt(
        [("class:prompt", "4) Select DESTINATION filesystem type (e.g. FAT32, NTFS, ext4): ")],
        completer=fs_completer,
        validator=Validator.from_callable(
            lambda t: t.strip() in FILESYSTEMS,
            error_message="Choose one of: " + ", ".join(FILESYSTEMS.keys()),
            move_cursor_to_end=True,
        ),
        style=style,
    ).strip()
    dest_allowed = FILESYSTEMS[dest_fs]

    # Copy / Move Logic
    op_completer = WordCompleter(["COPY", "MOVE"], ignore_case=True)
    operation = prompt(
        [("class:prompt", "5) Choose OPERATION (COPY or MOVE): ")],
        completer=op_completer,
        validator=Validator.from_callable(
            lambda t: t.strip().upper() in {"COPY", "MOVE"},
            error_message="Type COPY or MOVE",
            move_cursor_to_end=True,
        ),
        style=style,
    ).strip().upper()

    # If READONLY mount, switch to COPY
    if operation == "MOVE":
        if not os.access(str(source_root), os.W_OK):
            console.print(f"[yellow]Warning: Source {source_root} is not writable → cannot MOVE. Switching to COPY.[/yellow]")
            operation = "COPY"

    console.print(f"\n[bold]Summary:[/bold]\n  • Source:f [cyan]{source_root}[/cyan] (FS={source_fs})\n  • Destination: [cyan]{dest_root}[/cyan] (FS={dest_fs})\n  • Operation: [cyan]{operation}[/cyan]\n")

    # Scan for size and count
    total_files = 0
    total_bytes = 0
    console.print("[blue]Scanning source directory for files…[/blue]")
    for root, dirs, files in os.walk(source_root):
        for fname in files:
            total_files += 1
            filepath = Path(root) / fname
            try:
                total_bytes += filepath.stat().st_size
            except Exception:
                # If we can’t stat (permissions?), skip size count
                pass

    if total_files == 0:
        console.print(f"[red]No files found under {source_root}. Exiting.[/red]")
        sys.exit(0)

    # Show summary
    mib = total_bytes / (1024 * 1024)
    console.print(
        f"\nFound [green]{total_files}[/green] files totaling [green]{total_bytes} bytes (~{mib:.2f} MiB)."
    )

    # Confirm before proceeding
    proceed = prompt(
        [("class:prompt", "Proceed with transfer? (y/n): ")],
        validator=Validator.from_callable(
            lambda t: t.strip().lower() in {"y", "n"},
            error_message="Type y or n",
            move_cursor_to_end=True,
        ),
        style=style,
    ).strip().lower()
    if proceed != "y":
        console.print("[red]Operation canceled by user. Exiting.[/red]")
        sys.exit(0)


# Begin Transfer
    console.print("\n[blue]Transferring files…[/blue]\n")
    transferred_files = 0
    transferred_bytes = 0

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TransferSpeedColumn(),  
        "•",
        TimeRemainingColumn(),
    )
    task = progress.add_task(
        f"Copying files", total=total_bytes, start=False
    )

    with progress:
        progress.start_task(task)
        for root, dirs, files in os.walk(source_root):
            # Compute relative subpath under source_root
            rel_root = Path(root).relative_to(source_root)
            # Ensure corresponding subdirectory in destination exists
            dest_subdir = dest_root / rel_root
            dest_subdir.mkdir(parents=True, exist_ok=True)

            for fname in files:
                transferred_files += 1
                src_path = Path(root) / fname

                # Sanitize filename for destination if needed
                safe_name = sanitize_filename(fname, dest_allowed)
                if safe_name != fname:
                    console.print(f"[yellow]Renaming '{fname}' → '{safe_name}'[/yellow]")
                dst_path = dest_subdir / safe_name

                # Execute copy or move
                try:
                    fsize = src_path.stat().st_size
                except Exception:
                    fsize = 0

                if operation == "COPY":
                    try:
                        shutil.copy2(str(src_path), str(dst_path))
                    except Exception as e:
                        console.print(f"[red]Failed to COPY '{src_path}': {e}[/red]")
                        continue
                else:  # MOVE
                    try:
                        shutil.move(str(src_path), str(dst_path))
                    except Exception as e:
                        console.print(f"[red]Failed to MOVE '{src_path}': {e}[/red]")
                        continue

                transferred_bytes += fsize
                progress.update(task, advance=fsize, description=f"({transferred_files}/{total_files})")

        # All files done
        progress.update(task, completed=total_bytes)
    console.print(f"\n[bold green]Done! Transferred {transferred_files} files ({transferred_bytes} bytes).[/bold green]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Interrupted by user] Exiting.")
        sys.exit(0)
