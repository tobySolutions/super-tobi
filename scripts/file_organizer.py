#!/usr/bin/env python3
"""
Super Tobi — File Organizer
Scans directories, reports on file organization, and safely reorganizes files.
NEVER deletes files — only moves them.
"""

import argparse
import hashlib
import os
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.prompt import Confirm
from rich import box

console = Console()

# File type categories for organization
FILE_CATEGORIES = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".tiff", ".heic", ".heif"},
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".ods", ".numbers"},
    "Presentations": {".ppt", ".pptx", ".key", ".odp"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz", ".dmg"},
    "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp", ".h",
             ".rb", ".php", ".swift", ".kt", ".sol", ".toml", ".yaml", ".yml", ".json", ".xml",
             ".html", ".css", ".scss", ".less", ".sh", ".bash", ".zsh", ".fish"},
    "Executables": {".exe", ".msi", ".app", ".deb", ".rpm", ".pkg", ".AppImage"},
    "Fonts": {".ttf", ".otf", ".woff", ".woff2", ".eot"},
    "Design": {".psd", ".ai", ".sketch", ".fig", ".xd"},
    "Data": {".sql", ".db", ".sqlite", ".parquet", ".feather"},
}


def get_category(ext):
    """Get the category for a file extension."""
    ext_lower = ext.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext_lower in extensions:
            return category
    return "Other"


def file_hash(filepath, chunk_size=8192):
    """Get MD5 hash of first chunk of file for duplicate detection."""
    try:
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            chunk = f.read(chunk_size)
            h.update(chunk)
        return h.hexdigest()
    except (PermissionError, OSError):
        return None


def scan_directory(directory):
    """Scan a directory and collect file information."""
    directory = Path(directory).expanduser().resolve()

    if not directory.exists():
        console.print(f"[red]Directory not found:[/] {directory}")
        return None

    files = []
    errors = 0

    for root, dirs, filenames in os.walk(directory):
        # Skip hidden directories and common system dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", ".git", "venv", ".venv")]

        for fname in filenames:
            if fname.startswith("."):
                continue
            fpath = Path(root) / fname
            try:
                stat = fpath.stat()
                files.append({
                    "path": fpath,
                    "name": fname,
                    "ext": fpath.suffix,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                    "category": get_category(fpath.suffix),
                })
            except (PermissionError, OSError):
                errors += 1

    return {"directory": directory, "files": files, "errors": errors}


def cmd_scan(directory):
    """Scan and report on directory contents."""
    console.print(f"[bold cyan]Scanning:[/] {directory}\n")

    result = scan_directory(directory)
    if not result:
        return

    files = result["files"]
    if not files:
        console.print("[dim]No files found.[/]")
        return

    total_size = sum(f["size"] for f in files)

    # File types breakdown
    type_counts = defaultdict(lambda: {"count": 0, "size": 0})
    for f in files:
        cat = f["category"]
        type_counts[cat]["count"] += 1
        type_counts[cat]["size"] += f["size"]

    table = Table(title="File Types Breakdown", box=box.ROUNDED)
    table.add_column("Category", style="bold")
    table.add_column("Count", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("% of Total", justify="right")

    for cat, info in sorted(type_counts.items(), key=lambda x: -x[1]["size"]):
        pct = (info["size"] / total_size * 100) if total_size > 0 else 0
        table.add_row(
            cat,
            str(info["count"]),
            format_size(info["size"]),
            f"{pct:.1f}%",
        )

    table.add_row("", "", "", "")
    table.add_row("[bold]Total[/]", f"[bold]{len(files)}[/]", f"[bold]{format_size(total_size)}[/]", "100%")
    console.print(table)

    # Largest files
    largest = sorted(files, key=lambda f: -f["size"])[:10]
    ltable = Table(title="Largest Files", box=box.ROUNDED)
    ltable.add_column("File", style="bold", max_width=50)
    ltable.add_column("Size", justify="right", style="cyan")
    ltable.add_column("Category", style="dim")

    for f in largest:
        rel_path = str(f["path"].relative_to(result["directory"]))
        ltable.add_row(rel_path, format_size(f["size"]), f["category"])

    console.print(ltable)

    # Duplicates (by size + first-chunk hash)
    size_groups = defaultdict(list)
    for f in files:
        if f["size"] > 0:
            size_groups[f["size"]].append(f)

    duplicates = []
    for size, group in size_groups.items():
        if len(group) < 2:
            continue
        hash_groups = defaultdict(list)
        for f in group:
            h = file_hash(f["path"])
            if h:
                hash_groups[h].append(f)
        for h, hgroup in hash_groups.items():
            if len(hgroup) >= 2:
                duplicates.append(hgroup)

    if duplicates:
        dtable = Table(title=f"Potential Duplicates ({len(duplicates)} groups)", box=box.ROUNDED)
        dtable.add_column("Files", style="bold")
        dtable.add_column("Size", justify="right", style="yellow")

        for group in duplicates[:10]:
            names = "\n".join(str(f["path"].relative_to(result["directory"])) for f in group)
            dtable.add_row(names, format_size(group[0]["size"]))

        console.print(dtable)

    # Old files (> 1 year)
    one_year_ago = datetime.now() - timedelta(days=365)
    old_files = [f for f in files if f["modified"] < one_year_ago]
    if old_files:
        old_size = sum(f["size"] for f in old_files)
        console.print(Panel(
            f"[bold]{len(old_files)}[/] files older than 1 year\n"
            f"Total size: [yellow]{format_size(old_size)}[/]",
            title="[bold yellow]Old Files[/]",
            border_style="yellow",
        ))

    if result["errors"]:
        console.print(f"\n[dim]{result['errors']} files could not be read (permissions)[/]")


def cmd_organize(directory, confirm=False):
    """Generate or execute an organization plan."""
    console.print(f"[bold cyan]{'Organizing' if confirm else 'Planning organization for'}:[/] {directory}\n")

    result = scan_directory(directory)
    if not result:
        return

    files = result["files"]
    if not files:
        console.print("[dim]No files to organize.[/]")
        return

    base_dir = result["directory"]

    # Build the plan: group by category
    plan = defaultdict(list)
    for f in files:
        # Only organize files in the top level (not already in subdirectories)
        if f["path"].parent == base_dir:
            target_dir = base_dir / f["category"]
            plan[f["category"]].append({
                "from": f["path"],
                "to": target_dir / f["name"],
                "size": f["size"],
            })

    if not plan:
        console.print("[dim]All files are already in subdirectories. Nothing to organize.[/]")
        return

    # Show the plan
    tree = Tree(f"[bold]{base_dir}[/]")
    total_moves = 0

    for category in sorted(plan.keys()):
        moves = plan[category]
        total_moves += len(moves)
        branch = tree.add(f"[bold cyan]{category}/[/] ({len(moves)} files)")
        for move in moves[:5]:
            branch.add(f"[dim]{move['from'].name}[/]")
        if len(moves) > 5:
            branch.add(f"[dim]... +{len(moves) - 5} more[/]")

    console.print(tree)
    console.print(f"\n[bold]{total_moves} files[/] will be moved into category folders.")

    if not confirm:
        console.print("\n[yellow]This is a dry run.[/] Add [bold]--confirm[/] to execute.")
        return

    # Execute the plan
    moved = 0
    errors = 0

    for category, moves in plan.items():
        for move in moves:
            try:
                move["to"].parent.mkdir(parents=True, exist_ok=True)

                # Handle name conflicts
                target = move["to"]
                if target.exists():
                    stem = target.stem
                    suffix = target.suffix
                    counter = 1
                    while target.exists():
                        target = target.parent / f"{stem}_{counter}{suffix}"
                        counter += 1

                shutil.move(str(move["from"]), str(target))
                moved += 1
            except Exception as e:
                console.print(f"[red]Error moving {move['from'].name}:[/] {e}")
                errors += 1

    console.print(f"\n[bold green]Moved {moved} files.[/]")
    if errors:
        console.print(f"[red]{errors} errors occurred.[/]")


def cmd_downloads():
    """Organize ~/Downloads."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        console.print("[red]~/Downloads not found.[/]")
        return

    cmd_scan(str(downloads))
    console.print("\n[dim]To organize, run:[/] supertobi files organize ~/Downloads")
    console.print("[dim]To execute:[/]   supertobi files organize ~/Downloads --confirm")


def format_size(size_bytes):
    """Format bytes into human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


def main():
    parser = argparse.ArgumentParser(description="Super Tobi File Organizer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", metavar="DIR", help="Scan and report on a directory")
    group.add_argument("--organize", metavar="DIR", help="Suggest organization plan")
    group.add_argument("--cleanup", metavar="DIR", help="Execute organization plan")
    group.add_argument("--downloads", action="store_true", help="Scan ~/Downloads")

    parser.add_argument("--confirm", action="store_true", help="Actually execute changes (with --organize or --cleanup)")

    args = parser.parse_args()

    if args.scan:
        cmd_scan(args.scan)
    elif args.organize:
        cmd_organize(args.organize, confirm=args.confirm)
    elif args.cleanup:
        cmd_organize(args.cleanup, confirm=args.confirm)
    elif args.downloads:
        cmd_downloads()


if __name__ == "__main__":
    main()
