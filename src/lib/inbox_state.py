import json
import os
import time
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, cast, TypeVar

from src.lib.audiobook import Audiobook
from src.lib.formatters import friendly_short_date
from src.lib.fs_utils import (
    count_audio_files_in_inbox,
    find_book_dirs_in_inbox,
    find_books_in_inbox,
    find_standalone_books_in_inbox,
)
from src.lib.hasher import Hasher
from src.lib.inbox_item import get_item, get_key, InboxItem, InboxItemStatus
from src.lib.misc import singleton
from src.lib.strings import en
from src.lib.term import print_debug, print_notice

SCAN_CALLS = 0


def filter_series_parents(d: dict[str, "InboxItem"]):
    return {k: v for k, v in d.items() if not v.is_maybe_series_parent}


def scanner(func: Callable[..., Any]):
    """A decorator that scans the path of a Hasher object after calling the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        from src.lib.config import cfg

        hasher = cast(Hasher, args[0])
        result = func(*args, **kwargs)
        if hasher.hash_age > cfg.SLEEP_TIME:
            hasher.scan()
        return result

    return wrapper


R = TypeVar("R")


def requires_scan(func: Callable[..., R]):
    """A decorator that ensures the path of a Hasher object has been scanned before calling the decorated function."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        inbox = cast(InboxState, args[0])
        if not inbox._hashes or not inbox._last_run_start:
            inbox.scan(skip_failed_sync=True)
        return cast(R, func(*args, **kwargs))

    return wrapper


@singleton
class InboxState(Hasher):

    def __init__(self):
        from src.lib.config import cfg

        super().__init__(cfg.inbox_dir)
        self._items: dict[str, InboxItem] = {}
        self.ready = False
        self.loop_counter = 0
        self.banner_printed = False
        # print_debug("Set banner_printed to False")
        self._last_scan = 0

    def set(
        self,
        key_path_or_book: str | Path | Audiobook | InboxItem,
        *,
        status: InboxItemStatus | None = None,
        last_updated: float | None = None,
    ):
        item = get_item(key_path_or_book)

        self._items[item.key] = item
        if last_updated:
            self._items[item.key]._last_updated = last_updated
        if status:
            self._items[item.key].status = status

    @requires_scan
    def get(
        self, key_path_hash_or_book: str | Path | Audiobook | None
    ) -> InboxItem | None:
        if not key_path_hash_or_book:
            return None
        key = get_key(key_path_hash_or_book)
        simple = self._items.get(key, None)
        if simple:
            return simple
        return next(
            (
                item
                for item in self._items.values()
                if key in [item.key, item.hash, item.path]
            ),
            None,
        )

    def rm(self, key_path_book_or_hash: str | Path | Audiobook):
        key = get_key(key_path_book_or_hash)
        if key or (item := self.get(str(key_path_book_or_hash))) and (key := item.key):
            return self._items.pop(key, None)

    def scan(
        self,
        *paths: str | Path,
        recheck_failed: bool = False,
        skip_failed_sync: bool = False,
        set_ready: bool = False,
    ):
        from src.lib.config import cfg

        if time.time() - self._last_scan < cfg.WAIT_TIME:
            return

        if self.stale:
            recheck_failed = True

        global SCAN_CALLS
        SCAN_CALLS += 1

        super().scan()

        if paths:
            _paths = [
                p.relative_to(cfg.inbox_dir)
                for p in map(Path, paths)
                if not p.is_absolute()
            ]
        else:
            _paths = find_books_in_inbox()

        new_items = {p.name: InboxItem(p) for p in _paths}

        # smart_print(f"scan calls: {SCAN_CALLS}", SCAN_CALLS)
        # try:
        #     smart_print(
        #         self._items["old_mill__multidisc_mp3"].to_dict(refresh_hash=False)
        #     )
        # except:
        #     pass

        gone_keys = set(self._items.keys()) - set(new_items.keys())
        for k, v in new_items.items():
            if k not in self._items:
                self._items[k] = v
            elif recheck_failed and (item := self._items[k]):
                if item.status == "failed" and (
                    item.did_change or item.hash_age < cfg.SLEEP_TIME
                ):
                    item.set_needs_retry()

        # remove items that are no longer in the inbox
        for k in gone_keys:
            if item := self._items.get(k):
                item.set_gone()

        if not skip_failed_sync and not self.failed_books and os.getenv("FAILED_BOOKS"):
            _sync_failed_from_env()

        if set_ready:
            self.ready = True

        self._last_scan = time.time()
        self.stale = False

    def flush(self):
        super().flush()
        self._items = {}

    @property
    def match_filter(self):
        from src.lib.config import cfg

        if not cfg.MATCH_FILTER and (env := os.getenv("MATCH_FILTER")):
            self.set_match_filter(env)
            print_debug(
                f"Setting match filter from env: {cfg.MATCH_FILTER} (was not previoulsy set in state)"
            )
        return cfg.MATCH_FILTER

    def set_match_filter(self, match_filter: str | None):
        from src.lib.config import cfg

        if match_filter is None:
            os.environ.pop("MATCH_FILTER", None)
            # update all items where filtered was set to ok
            for d in self.filtered_books:
                if item := self.get(d):
                    item.set_ok()
            cfg.MATCH_FILTER = ""
            return

        os.environ["MATCH_FILTER"] = match_filter
        cfg.MATCH_FILTER = match_filter

    def reset_inbox(self, new_match_filter: str | None = None):

        self.set_match_filter(new_match_filter)
        self.flush()
        self.ready = False
        _sync_failed_from_env()
        self.reset_loop_counter()
        return self

    def clear_failed(self):
        for item in self.failed_books.values():
            item.set_ok()
        _sync_failed_to_env()

    def reset_loop_counter(self, start_at: int = 0):
        self.loop_counter = start_at

    @requires_scan
    def did_fail(self, key_path_or_book: str | Path | Audiobook):
        if item := self.get(key_path_or_book):
            return item.status == "failed"
        return False

    @requires_scan
    def should_retry(self, key_path_or_book: str | Path | Audiobook):
        if item := self.get(key_path_or_book):
            return item.status == "needs_retry"
        return False

    @requires_scan
    def is_filtered(self, key_or_path: str | Path | Audiobook):
        if item := self.get(key_or_path):
            return item.is_filtered
        return False

    @requires_scan
    def is_ok(self, key_path_or_book: str | Path | Audiobook):
        if item := self.get(key_path_or_book):
            return item.status in ["ok", "new"]
        return False

    @property
    def items(self):
        return self._items

    @property
    def num_audio_files_deep(self):
        return count_audio_files_in_inbox()

    @property
    def standalone_files(self):
        return find_standalone_books_in_inbox()

    @property
    def standalone_books(self):
        return {
            k: v
            for k, v in self._items.items()
            if v.is_file and v.status in ("ok", "new", "needs_retry")
        }

    @property
    def num_standalone_books(self):
        return len(self.standalone_books)

    @property
    def book_dirs(self):
        return find_book_dirs_in_inbox()

    @property
    def series_parents(self):
        return find_book_dirs_in_inbox(only_series_parents=True)

    def series_items_for_key(self, key: str):
        return [
            v
            for _k, v in self._items.items()
            if v.series_key == key
            or Path(v.key).parts[0] == key
            and v.is_maybe_series_book
        ]

    @property
    def num_books(self):
        return len(self.book_dirs) - len(self.series_parents)

    @property
    def num_series(self):
        return len(self.series_parents)

    @property
    def filtered_books(self):
        return {k: v for k, v in self._items.items() if v.is_filtered}

    @property
    def num_filtered(self):
        return len(self.filtered_books)

    @property
    def matched_books(self):
        return filter_series_parents(
            {
                k: v
                for k, v in self._items.items()
                if not v.is_filtered and not v.status in ["gone"]
            }
        )

    @property
    def num_matched(self):
        return len(self.matched_books)

    @property
    def ok_books(self):
        return filter_series_parents(
            {
                k: v
                for k, v in self._items.items()
                if v.status in ["ok", "new", "needs_retry"]
            }
        )

    @property
    def num_ok(self):
        return len(self.ok_books)

    @property
    def matched_ok_books(self):
        return {k: v for k, v in self.ok_books.items() if k in self.matched_books}

    @property
    def num_matched_ok(self):
        return len(self.matched_ok_books)

    @property
    def has_failed_books(self):
        return any(v.status in ["failed", "needs_retry"] for v in self._items.values())

    @property
    def failed_books(self):
        return {k: v for k, v in self._items.items() if v.status == "failed"}

    @property
    def num_failed(self):
        return len(self.failed_books)

    @property
    def all_books_failed(self):
        haystack = (
            self._items.values()
            if not self.match_filter
            else self.matched_books.values()
        )
        return all(v.status == "failed" for v in haystack)

    @requires_scan
    def start(self):
        if len(self._hashes):
            self._last_run_start = self._hashes[0]

    @scanner
    def done(self):
        if len(self._hashes):
            self._last_run_end = self._hashes[0]
        self.banner_printed = False
        # print_debug("Set banner_printed to False")

    @property
    @scanner
    def changed_since_last_run_started(self):
        changed = self.next_hash != self.last_run_start_hash
        if changed:
            self.stale = True
        return changed

    @property
    @scanner
    def changed_since_last_run_ended(self):
        changed = self.next_hash != self.last_run_end_hash
        if changed:
            self.stale = True
        return changed

    def inbox_needs_processing(self, *, on_will_scan: Callable[[], None] | None = None):

        from src.lib.config import cfg
        from src.lib.run import print_banner

        self.changed_after_waiting = False
        waited_count = 0
        before_modified_hash = (
            self.prev_hash if self.hash_age < cfg.SLEEP_TIME else self.curr_hash
        )
        _banner_printed = False
        # rec_mod = self.dir_was_recently_modified
        while self.dir_was_recently_modified:
            print_debug(
                f"{en.DEBUG_WAITING_FOR_INBOX} {waited_count + 1} ({before_modified_hash} → {self.curr_hash})"
            )
            self.scan()
            if not self.changed_after_waiting:
                self.changed_after_waiting = self.next_hash != before_modified_hash

            if self.changed_after_waiting and not _banner_printed:
                self.stale = True
                print_banner(
                    after=lambda: print_notice(f"{en.INBOX_RECENTLY_MODIFIED}\n")
                )
                _banner_printed = True

            waited_count += 1
            time.sleep(0.5)

        needs_scan = (
            self.changed_since_last_run_ended or self.changed_since_last_run_started
        )

        # print_debug(
        #     f"----------------------------\n"
        #     f"        Recently modified: {rec_mod}\n"
        #     f"        Last run hash: {self.last_run_hash}\n"
        #     f"        Prev hash: {self.previous_hash}\n"
        #     f"        Curr hash: {self.current_hash}\n"
        #     f"        Next hash: {self.next_hash}\n"
        #     f"        Changed after waiting: {changed_after_waiting}\n"
        #     f"        Changed since last run: {self.changed_since_last_run}\n"
        #     f"        Needs processing: {needs_processing}\n"
        #     f"        Waited count: {waited_count}\n"
        #     f"        Ready: {self.ready}\n"
        # )

        if needs_scan or waited_count > 0:

            hash_changed = self.curr_hash != before_modified_hash

            msg = ""
            if waited_count:
                msg = f"Done waiting for inbox"

            # Fix standalone files
            if on_will_scan:
                on_will_scan()

            self.scan(recheck_failed=True, set_ready=True)

            if hash_changed:
                h = f"({before_modified_hash} → {self.curr_hash})"
                msg = f"{msg} - hash changed {h}" if msg else f"Hash changed {h}"
                print_banner()

            elif msg:
                msg = f"{msg}, no changes ({self.curr_hash})"

            if msg:
                print_debug(f"{msg}", only_once=True)

            if self.matched_ok_books or hash_changed:

                # print_debug(f"{len(self.matched_ok_books)} book(s) need processing")
                return True

        print_debug(
            f"{en.DEBUG_INBOX_HASH_UNCHANGED} {friendly_short_date(self.last_hash_change)} ({self.curr_hash})",
            only_once=True,
        )

        return False

    def to_dict(self, refresh_hashes=False):
        return {
            path: item.to_dict(refresh_hashes) for path, item in self._items.items()
        }

    @property
    def fixed_books(self):
        return {
            k: v
            for k, v in self._items.items()
            if v.status == "needs_retry" and v.failed_reason
        }

    def set_failed(
        self,
        key_path_or_book: str | Path | Audiobook,
        reason: str,
        last_updated: float | None = None,
    ):
        if not self.get(key_path_or_book):
            self.set(key_path_or_book)

        if item := self.get(key_path_or_book):
            item.set_failed(reason)
            if last_updated is not None:
                item._last_updated = last_updated
            _sync_failed_to_env()
        else:
            print_debug(f"Item {key_path_or_book} not found in inbox")

    def set_needs_retry(self, key_path_or_book: str | Path | Audiobook):
        if not self.get(key_path_or_book):
            self.set(key_path_or_book)

        if item := self.get(key_path_or_book):
            item.set_needs_retry()
            _sync_failed_to_env()
        else:
            print_debug(f"Item {key_path_or_book} not found in inbox")

    def set_ok(self, key_path_or_book: str | Path | Audiobook):
        if not self.get(key_path_or_book):
            self.set(key_path_or_book)

        if item := self.get(key_path_or_book):
            item.set_ok()
            _sync_failed_to_env()
        else:
            print_debug(f"Item {key_path_or_book} not found in inbox")

    def set_gone(self, key_path_or_book: str | Path | Audiobook):
        if not self.get(key_path_or_book):
            self.set(key_path_or_book)

        if item := self.get(key_path_or_book):
            item.set_gone()
            _sync_failed_to_env()
        else:
            print_debug(f"Item {key_path_or_book} not found in inbox")

    def __iter__(self):
        return iter(self._items.values())

    def __len__(self):
        return len(self._items)

    def __contains__(self, path: Path):
        return path in self._items

    def __repr__(self):
        return f"Inbox state:\n{self.__str__()}"

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


def _sync_failed_to_env():
    os.environ["FAILED_BOOKS"] = json.dumps(
        {k: v.last_updated for k, v in InboxState().failed_books.items()}
    )


def _sync_failed_from_env():
    failed_books = {
        k: float(v) for k, v in json.loads(os.getenv("FAILED_BOOKS", "{}")).items()
    }
    for k, lu in failed_books.items():
        InboxState().set_failed(k, "From ENV", lu)
