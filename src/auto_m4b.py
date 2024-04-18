import sys
import time
import traceback
from contextlib import contextmanager

from src.lib import run
from src.lib.config import AutoM4bArgs, cfg
from src.lib.inbox_state import InboxState
from src.lib.term import nl, print_error, print_red, was_prev_line_empty
from src.lib.typing import copy_kwargs_omit_first_arg


def handle_err(e: Exception):

    from src.lib.config import cfg

    with open(cfg.FATAL_FILE, "a") as f:
        f.write(f"Fatal {e}")

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
    with use_error_handler():
        args = AutoM4bArgs(**kwargs)
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
