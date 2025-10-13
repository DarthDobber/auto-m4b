import os
import sys
import time
import traceback
from contextlib import contextmanager

from src.lib.config import AutoM4bArgs
from src.lib.typing import copy_kwargs_omit_first_arg


def handle_err(e: Exception):

    from src.lib.config import cfg
    from src.lib.term import print_error, print_red

    with open(cfg.FATAL_FILE, "a") as f:
        f.write(str(e))

    if cfg.DEBUG:
        print_red(f"\n{traceback.format_exc()}")
    else:
        print_error(f"Error: {e}")

    if "pytest" in sys.modules:
        raise e

    time.sleep(cfg.SLEEP_TIME)


@contextmanager
def use_error_handler():
    try:
        yield
    except Exception as e:
        handle_err(e)


@copy_kwargs_omit_first_arg(AutoM4bArgs.__init__)
def app(**kwargs):
    args = AutoM4bArgs(**kwargs)

    # Handle --help-config flag (no error handler needed)
    if args.help_config:
        from src.lib.config import Config
        Config.print_config_help()
        sys.exit(0)

    # Handle --validate flag (with error handler for config issues)
    if args.validate:
        from src.lib.term import print_green, print_red
        from src.lib.config import cfg

        try:
            with cfg.load_env(args, quiet=True):
                pass
            print("\nValidating configuration...\n")

            is_valid, errors = cfg.validate_config()

            if is_valid:
                print_green("✓ Configuration is valid!\n")
                print("Configuration summary:")
                print(f"  INBOX_FOLDER:     {cfg.inbox_dir}")
                print(f"  CONVERTED_FOLDER: {cfg.converted_dir}")
                print(f"  ARCHIVE_FOLDER:   {cfg.archive_dir}")
                print(f"  BACKUP_FOLDER:    {cfg.backup_dir}")
                print(f"  FAILED_FOLDER:    {cfg.failed_dir}")
                print(f"  CPU_CORES:        {cfg.CPU_CORES}")
                print(f"  MAX_RETRIES:      {cfg.MAX_RETRIES}")
                print(f"  SLEEP_TIME:       {cfg.SLEEP_TIME}s")
                print(f"  m4b-tool:         {cfg.m4b_tool_version}")
                print()
                sys.exit(0)
            else:
                print_red("✗ Configuration validation failed:\n")
                for error in errors:
                    print_red(f"  • {error}")
                print()
                sys.exit(1)
        except Exception as e:
            print_red(f"✗ Configuration validation failed:\n")
            print_red(f"  • {e}")
            print()
            sys.exit(1)

    # Import these after flag checks to avoid config errors
    from src.lib import run
    from src.lib.config import cfg
    from src.lib.inbox_state import InboxState
    from src.lib.term import nl, was_prev_line_empty

    with use_error_handler():

        infinite_loop = args.max_loops == -1
        inbox = InboxState()
        inbox.loop_counter += 1
        cfg.startup(args)
        while infinite_loop or inbox.loop_counter <= args.max_loops:
            try:
                run.process_inbox()
            finally:
                inbox.loop_counter += 1
                if infinite_loop or inbox.loop_counter <= args.max_loops:
                    time.sleep(cfg.SLEEP_TIME)

        if not was_prev_line_empty():
            nl()


if __name__ == "__main__":
    app()
