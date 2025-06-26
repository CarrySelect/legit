import os
import sys
from pathlib import Path

import click

from legit.cmd_base import Base


CONTEXT_SETTINGS = {
    "help_option_names": ["-h", "--help"],
    "max_content_width": 120,
}

def run_cmd(cmd_name: str, *args: str) -> None:
    from legit.command import Command

    argv: list[str] = ["legit", cmd_name, *args]
    
    cmd: Base = Command.execute(
        Path.cwd(),
        os.environ.copy(),
        argv,
        sys.stdin,
        sys.stdout,
        sys.stderr,
    )
    
    sys.exit(cmd.status)



@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.argument("path", type=click.Path(file_okay=False, path_type=Path), required=False)
def init(path: Path | None) -> None:
    """Create an empty Legit repository in *PATH* (defaults to current dir)."""

    run_cmd("init", *(str(path),) if path is not None else ())


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("paths", nargs=-1, type=click.Path(path_type=Path))
def add(paths: tuple[Path, ...]) -> None:
    """Add file contents of *PATHS* to the index (staging area)."""

    # Git treats “legit add” with no paths as an error; here we mimic that.
    if not paths:
        click.echo("error: pathspec required", err=True)
        raise SystemExit(1)

    run_cmd("add", *(str(p) for p in paths))


@cli.command()
@click.pass_context
def commit(ctx: click.Context) -> None:
    """Record changes to the repository using the message from *STDIN*."""

    if sys.stdin.isatty():
        click.echo("error: commit message required via stdin", err=True)
        ctx.exit(1)

    run_cmd("commit")


@cli.command()
@click.option("--porcelain", is_flag=True, help="Machine‑readable output.")
def status(porcelain: bool) -> None:
    """Show the working tree status."""

    run_cmd("status", *("--porcelain",) if porcelain else ())



@cli.command(name="diff")
@click.option("--cached", "--staged", is_flag=True, help="Compare index with HEAD.")
def diff_cmd(cached: bool) -> None:
    """Show changes between index/HEAD or index/worktree."""

    run_cmd("diff", *("--cached",) if cached else ())


@cli.command()
@click.option('-v', '--verbose', is_flag=True, help='Show verbose branch output')
@click.option('-d', '--delete', 'delete', is_flag=True, help='Delete a branch')
@click.option('-f', '--force', 'force', is_flag=True, help='Force delete a branch')
@click.option('-D', 'D', is_flag=True, help='Shortcut for --delete --force')
@click.argument('name', required=False)
@click.argument('start', required=False)
def branch(verbose: bool, delete: bool, force: bool, D: bool, name: str | None, start: str | None) -> None:
    """List, create, or delete branches."""
    flags = []
    if verbose:
        flags.append('-v')
    if delete or D:
        flags.append('-d')
    if force or D:
        flags.append('-f')
    if D and not (delete and force):
        # If -D used alone, ensure both delete and force get set
        flags = [f for f in flags if f not in ('-d', '-f')]
        flags.extend(['-D'])
    
    # Build positional args
    args = []
    if name:
        args.append(name)
    if start:
        args.append(start)
    
    run_cmd('branch', *flags, *args)

@cli.command()
@click.argument("target")
def checkout(target: str) -> None:
    """Switch branches or restore files."""

    run_cmd("checkout", target)


@cli.command()
@click.option(
    "--abbrev-commit/--no-abbrev-commit",
    "abbrev",
    default=None,
    help="Use abbreviated commit hashes.",
)
@click.option(
    "--pretty",
    "--format",
    "format_",
    default="medium",
    metavar="<format>",
    help="Pretty-print format (e.g., medium, oneline).",
)
@click.option(
    "--oneline",
    is_flag=True,
    help="Shortcut for --pretty=oneline --abbrev-commit.",
)
@click.option(
    "--decorate",
    "decoration",
    type=click.Choice(["short", "full", "no", "auto"], case_sensitive=False),
    default="auto",
    show_default=True,
    help="Decorate refs. 'auto' is default, 'no' disables.",
)
@click.option(
    "--patch", "-p",
    "patch",
    is_flag=True,
    help="Show patch for each commit.",
)
@click.argument("revisions_and_paths", nargs=-1)
def log(abbrev: bool | None, format_: str, oneline: bool, decoration: str, patch: bool, revisions_and_paths: tuple[str, ...]):
    """Display commit history."""
    
    # Process the --oneline shortcut, which overrides other format options
    # and implies abbreviation unless explicitly disabled.
    if oneline:
        format_ = "oneline"
        if abbrev is None:  # Only default to abbrev if it wasn't set explicitly
            abbrev = True

    # Prepare the list of arguments for the backend command
    cmd_args = ["log"]

    # Add flags based on the final processed options
    if abbrev is True:
        cmd_args.append("--abbrev-commit")
    elif abbrev is False:
        cmd_args.append("--no-abbrev-commit")

    # Add pretty format if it's not the default
    if format_ != "medium":
        # The --oneline flag is the canonical way to get that format
        if format_ == "oneline":
             cmd_args.append("--oneline")
        else:
             cmd_args.append(f"--pretty={format_}")
    
    # Add decoration flag unless it's the default 'auto'
    if decoration != "auto":
        if decoration == "no":
            cmd_args.append("--no-decorate")
        else:
            # For 'short' or 'full'. This matches git's --decorate=<format>
            cmd_args.append(f"--decorate={decoration}")

    if patch:
        cmd_args.append("--patch")
    
    # Add any remaining arguments (revisions, paths)
    if revisions_and_paths:
        cmd_args.extend(revisions_and_paths)

    # Execute the command with the constructed arguments
    run_cmd(*cmd_args)


if __name__ == '__main__':
    cli()
