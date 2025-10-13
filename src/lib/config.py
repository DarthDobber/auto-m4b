import argparse
import functools
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, cast, Literal, overload, TypeVar

from src.lib.formatters import listify
from src.lib.misc import (
    get_git_root,
    is_boolish,
    is_floatish,
    is_intish,
    is_maybe_path,
    is_noneish,
    load_env,
    parse_bool,
    parse_float,
    parse_int,
    pathify,
    set_typed_env_var,
    singleton,
    to_json,
)
from src.lib.strings import en
from src.lib.term import nl, print_amber, print_banana, print_debug, print_error
from src.lib.typing import OverwriteMode

DEFAULT_SLEEP_TIME: float = 10
DEFAULT_WAIT_TIME: float = 5
AUDIO_EXTS = [".mp3", ".m4a", ".m4b", ".wma"]
OTHER_EXTS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".heic",
    ".svg",
    ".epub",
    ".mobi",
    ".azw",
    ".pdf",
    ".txt",
    ".log",
]

IGNORE_FILES = [
    ".DS_Store",
    "._*",
    ".AppleDouble",
    ".LSOverride",
    ".Spotlight-V100",
    ".Trashes",
    "__MACOSX",
    "Desktop.ini",
    "ehthumbs.db",
    "Thumbs.db",
    "@eaDir",
]

WORKING_DIRS = [
    "BUILD_FOLDER",
    "MERGE_FOLDER",
    "TRASH_FOLDER",
]

OnComplete = Literal["archive", "delete", "test_do_nothing"]

parser = argparse.ArgumentParser(exit_on_error=False)
parser.add_argument("--env", help="Path to .env file", type=Path)
parser.add_argument(
    "--debug",
    help="Enable/disable debug mode (--debug=off to disable)",
    action="store",
    nargs="?",
    const=True,
    default=False,
    type=lambda x: False if str(x).lower() == "off" else True,
)
parser.add_argument(
    "--test",
    help="Enable/disable test mode (--test off to disable)",
    action="store",
    nargs="?",
    const=True,
    default=False,
    type=lambda x: False if str(x).lower() == "off" else True,
)
parser.add_argument(
    "-l",
    "--max_loops",
    help="Max number of times the app should loop (default: -1, infinity)",
    default=-1,
    type=int,
)
parser.add_argument(
    "--match",
    help="Only process books that contain this string in their filename. May be a regex pattern, but \\ must be escaped → '\\\\'. Default is None.",
    dest="match_filter",
    type=str,
    default=None,
)
parser.add_argument(
    "--validate",
    help="Validate configuration and exit",
    action="store_true",
    default=False,
)
parser.add_argument(
    "--help-config",
    help="Show all configuration options and exit",
    action="store_true",
    default=False,
)

T = TypeVar("T", bound=object)
D = TypeVar("D")


@overload
def pick(a: T, b) -> T: ...


@overload
def pick(a: T, b, default: None = None) -> T | None: ...


@overload
def pick(a, b, default: T) -> T: ...


def pick(a: T, b, default: D = None) -> T | D:
    if a is not None:
        return cast(T | D, a)
    if b is not None:
        return b
    return default


def env_property(
    typ: type[D] = str,
    default: D | None = None,
    var_name: str | None = None,
    on_get: Callable[[D], D] | None = None,
    on_set: Callable[[D | None], D | None] | None = None,
    del_on_none: bool = True,
):
    def decorator(func):
        if not ("self" in func.__code__.co_varnames):
            raise ValueError("Function must have a 'self' argument")

        key = func.__name__.upper().lstrip("_")

        @functools.wraps(func)
        def getter(self: "Config", *args, **kwargs):
            if not key in self._env or self._env[key] is None:
                env_value = os.getenv(var_name or key, default)
                if is_boolish(env_value) or typ == bool:
                    self._env[key] = parse_bool(env_value)
                elif typ == int or (is_intish(env_value) and typ != float):
                    self._env[key] = parse_int(env_value)
                elif is_floatish(env_value) or typ == float:
                    self._env[key] = parse_float(env_value)
                elif is_noneish(env_value):
                    if default is not None:
                        self._env[key] = default
                    elif del_on_none:
                        self._env.pop(key, None)
                    else:
                        self._env[key] = None
                elif is_maybe_path(env_value) or typ == Path:
                    self._env[key] = pathify(key, env_value)
                else:
                    self._env[key] = str(env_value)

            if on_get:
                return on_get(self._env[key])

            return cast(D, self._env.get(key, default))

        @functools.wraps(func)
        def setter(self: "Config", value: D | None):

            if on_set:
                value = on_set(value)

            if value is None and del_on_none:
                self._env.pop(key, None)
                os.environ.pop(key, None)
            else:
                self._env[key] = value
                os.environ[var_name or key] = str(value)

        return cast(D, property(getter, setter))

    return cast(Callable[..., D], decorator)


class AutoM4bArgs:
    env: Path | None
    debug: bool | None
    test: bool | None
    max_loops: int
    match_filter: str | None
    validate: bool
    help_config: bool

    def __init__(
        self,
        env: Path | None = None,
        debug: bool | None = None,
        test: bool | None = None,
        max_loops: int | None = None,
        match_filter: str | None = None,
        validate: bool = False,
        help_config: bool = False,
    ):
        args = parser.parse_known_args()[0]

        self.env = pick(env, args.env)
        self.debug = pick(debug, args.debug, None)
        self.test = pick(test, args.test, None)
        self.max_loops = pick(max_loops, args.max_loops, -1)
        self.match_filter = pick(match_filter, args.match_filter)
        # For boolean flags, prioritize argparse result if True (to respect CLI flags)
        self.validate = args.validate if args.validate else validate
        self.help_config = args.help_config if args.help_config else help_config

    def __str__(self) -> str:
        return to_json(self.__dict__)

    def __repr__(self) -> str:
        return f"AutoM4bArgs({self.__str__()})"


def ensure_dir_exists_and_is_writable(path: Path, throw: bool = True) -> None:
    from src.lib.term import print_warning

    path.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    is_writable = os.access(path, os.W_OK)

    if not exists:
        raise FileNotFoundError(f"{path} does not exist and could not be created")

    if not is_writable:
        if throw:
            raise PermissionError(
                f"{path} is not writable by current user, please fix permissions and try again"
            )
        else:
            print_warning(
                f"Warning: {path} is not writable by current user, this may result in data loss"
            )
            return


@contextmanager
def use_pid_file():
    from src.lib.config import cfg

    # read the pid file and look for a line starting with `FATAL` in all caps, if so, the app crashed and we should exit
    if cfg.FATAL_FILE.exists():
        err = f"auto-m4b fatally crashed on last run, once the problem is fixed, please delete the following lock file to continue:\n\n {cfg.FATAL_FILE}\n\n{cfg.FATAL_FILE.open().read()}"
        print_error(err)
        raise RuntimeError(err)

    already_exists = cfg.PID_FILE.is_file()

    if not cfg.PID_FILE.is_file():
        cfg.PID_FILE.touch()
        current_local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pid = os.getpid()
        cfg.PID_FILE.write_text(
            f"auto-m4b started at {current_local_time}, watching {cfg.inbox_dir} - pid={pid}\n"
        )

    try:
        yield already_exists
    finally:
        cfg.PID_FILE.unlink(missing_ok=True)


@singleton
class Config:
    _env: dict[str, Any] = {}
    _dotenv_src: Any = None
    _USE_DOCKER = False
    _last_debug_print: str = ""

    def __init__(self):
        """Do a first load of the environment variables in case we need them before the app runs."""
        # Try to load env, but allow failure for --help-config and --validate flags
        # This prevents errors when showing help before config is set up
        try:
            self.load_env(quiet=True)
        except Exception as e:
            # Config not set up yet - that's okay for help/validate commands
            # Silently ignore all config errors during initialization
            pass

    def startup(self, args: AutoM4bArgs | None = None):
        from src.lib.inbox_state import InboxState
        from src.lib.term import print_dark_grey, print_grey, print_mint

        start_time = time.perf_counter()

        with use_pid_file() as pid_exists:
            with self.load_env(args) as env_msg:
                if self.SLEEP_TIME and not "pytest" in sys.modules:
                    time.sleep(min(2, self.SLEEP_TIME / 2))

                if not pid_exists and not InboxState().loop_counter > 1:
                    print_mint("\nStarting auto-m4b...")
                    print_grey(self.info_str)
                    if env_msg:
                        print_dark_grey(env_msg)

                    beta_features = [
                        (
                            en.FEATURE_FLATTEN_MULTI_DISC_BOOKS,
                            self.FLATTEN_MULTI_DISC_BOOKS,
                        ),
                        (en.FEATURE_CONVERT_SERIES, self.CONVERT_SERIES),
                    ]

                    if test_debug_msg := (
                        "TEST + DEBUG modes on"
                        if self.TEST and self.DEBUG
                        else (
                            "TEST mode on"
                            if self.TEST
                            else "DEBUG mode on" if self.DEBUG else ""
                        )
                    ):
                        print_amber(test_debug_msg)

                    if beta_msg := (
                        f"[Beta] features are enabled:\n{listify([f for f, b in beta_features if b])}\n"
                        if any(b for _f, b in beta_features)
                        else ""
                    ):
                        print_banana(beta_msg)

        nl()

        self.clean()

        self.clear_cached_attrs()
        self.check_dirs()
        self.check_m4b_tool()

        elapsed_time = time.perf_counter() - start_time
        print_debug(f"Startup took {elapsed_time:.2f}s")

    @env_property(
        typ=str,
        on_get=lambda v: v if str(v).lower() not in ["none", ""] else None,
        on_set=lambda v: v if str(v).lower() not in ["none", ""] else None,
        del_on_none=False,
    )
    def _MATCH_FILTER(self): ...

    MATCH_FILTER = _MATCH_FILTER

    @env_property(
        typ=OnComplete,
        default="test_do_nothing" if "pytest" in sys.modules else "archive",
    )
    def _ON_COMPLETE(self): ...

    ON_COMPLETE = cast(OnComplete, _ON_COMPLETE)

    @env_property(
        var_name="OVERWRITE_EXISTING",
        typ=OverwriteMode,
        default="skip",
        on_get=lambda v: "overwrite" if parse_bool(v) else "skip",
        on_set=lambda v: "Y" if v == "overwrite" else "N",
    )
    def _OVERWRITE_MODE(self): ...

    OVERWRITE_MODE = cast(OverwriteMode, _OVERWRITE_MODE)

    @env_property(typ=bool, default=False)
    def _NO_CATS(self) -> bool: ...

    NO_CATS = _NO_CATS

    @env_property(typ=int, default=cpu_count())
    def _CPU_CORES(self): ...

    CPU_CORES = _CPU_CORES

    @env_property(typ=float, default=DEFAULT_SLEEP_TIME)
    def _SLEEP_TIME(self):
        """Time to sleep between loops, in seconds. Default is 10s."""
        ...

    SLEEP_TIME = _SLEEP_TIME

    @env_property(typ=float, default=DEFAULT_WAIT_TIME)
    def _WAIT_TIME(self):
        """Time to wait when a dir has been recently modified, in seconds. Default is 5s."""
        ...

    WAIT_TIME = _WAIT_TIME

    @property
    def sleeptime_friendly(self):
        """If it can be represented as a whole number, do so as {number}s
        otherwise, show as a float rounded to 1 decimal place, e.g. 0.1s"""
        return (
            f"{int(self.SLEEP_TIME)}s"
            if self.SLEEP_TIME.is_integer()
            else f"{self.SLEEP_TIME:.1f}s"
        )


    @env_property(typ=bool, default=False)
    def _USE_FILENAMES_AS_CHAPTERS(self): ...

    USE_FILENAMES_AS_CHAPTERS = _USE_FILENAMES_AS_CHAPTERS

    @env_property(typ=bool, default="pytest" in sys.modules)
    def _TEST(self): ...

    TEST = _TEST

    @env_property(typ=bool, default="pytest" in sys.modules)
    def _DEBUG(self): ...

    DEBUG = _DEBUG

    @env_property(typ=bool, default=True)
    def _BACKUP(self): ...

    BACKUP = _BACKUP

    @env_property(typ=bool, default=False)
    def _FLATTEN_MULTI_DISC_BOOKS(self): ...

    FLATTEN_MULTI_DISC_BOOKS = _FLATTEN_MULTI_DISC_BOOKS

    @env_property(typ=bool, default=False)
    def _CONVERT_SERIES(self): ...

    CONVERT_SERIES = _CONVERT_SERIES

    @env_property(typ=int, default=3)
    def _MAX_RETRIES(self):
        """Maximum number of times to retry a failed book (default: 3)"""
        ...

    MAX_RETRIES = _MAX_RETRIES

    @env_property(typ=bool, default=True)
    def _RETRY_TRANSIENT_ERRORS(self):
        """Whether to automatically retry transient errors (default: True)"""
        ...

    RETRY_TRANSIENT_ERRORS = _RETRY_TRANSIENT_ERRORS

    @env_property(typ=int, default=60)
    def _RETRY_BASE_DELAY(self):
        """Base delay in seconds for exponential backoff (default: 60)"""
        ...

    RETRY_BASE_DELAY = _RETRY_BASE_DELAY

    @env_property(typ=bool, default=True)
    def _MOVE_FAILED_BOOKS(self):
        """Whether to move failed books to the failed folder after max retries (default: True)"""
        ...

    MOVE_FAILED_BOOKS = _MOVE_FAILED_BOOKS

    @property
    def MAX_LOOPS(self):
        return self.args.max_loops if self.args.max_loops else -1

    @property
    def args(self) -> AutoM4bArgs:
        if not hasattr(self, "_ARGS"):
            self._args = AutoM4bArgs()
        return self._args

    @property
    def env(self):
        return self._env

    @cached_property
    def m4b_tool_version(self):
        """Runs m4b-tool --version"""
        return (
            subprocess.check_output(f"{self.m4b_tool} m4b-tool --version", shell=True)
            .decode()
            .strip()
        )

    @cached_property
    def _m4b_tool(self):
        """Note: if you are using the Dockerized version of m4b-tool, this will always be `m4b-tool`, because the pre-release version is baked into the image."""
        return ["m4b-tool"]

    @property
    def m4b_tool(self):
        return " ".join(self._m4b_tool)

    @cached_property
    def info_str(self):
        info = f"{self.CPU_CORES} CPU cores / "
        info += f"{self.sleeptime_friendly} sleep / "
        if self.USE_DOCKER:
            info += f"{self.m4b_tool_version} (Docker)"
        else:
            info += f"{self.m4b_tool_version}"

        return info

    @cached_property
    def AUDIO_EXTS(self):
        if env_audio_exts := os.getenv("AUDIO_EXTS"):
            global AUDIO_EXTS
            AUDIO_EXTS = env_audio_exts.split(",")
        return AUDIO_EXTS

    @cached_property
    def OTHER_EXTS(self):
        global OTHER_EXTS
        return OTHER_EXTS

    @cached_property
    def IGNORE_FILES(self):
        global IGNORE_FILES
        return IGNORE_FILES

    @cached_property
    def USE_DOCKER(self):
        self.check_m4b_tool()
        return self._USE_DOCKER

    @cached_property
    def docker_path(self):
        env_path = self.load_path_env("DOCKER_PATH", allow_empty=True)
        return env_path or shutil.which("docker")

    @cached_property
    def inbox_dir(self):
        return self.load_path_env("INBOX_FOLDER", allow_empty=False)

    @cached_property
    def converted_dir(self):
        return self.load_path_env("CONVERTED_FOLDER", allow_empty=False)

    @cached_property
    def archive_dir(self):
        return self.load_path_env("ARCHIVE_FOLDER", allow_empty=False)

    @cached_property
    def backup_dir(self):
        return self.load_path_env("BACKUP_FOLDER", allow_empty=False)

    @cached_property
    def failed_dir(self):
        return self.load_path_env("FAILED_FOLDER", allow_empty=False)

    @cached_property
    def tmp_dir(self):
        t = Path(tempfile.gettempdir()).resolve() / "auto-m4b"
        t.mkdir(parents=True, exist_ok=True)
        return t

    @cached_property
    def working_dir(self):
        """The working directory for auto-m4b, defaults to /<tmpdir>/auto-m4b."""
        d = self.load_path_env("WORKING_FOLDER", None, allow_empty=True)
        if not d:
            return self.tmp_dir
        d.mkdir(parents=True, exist_ok=True)
        return d

    @cached_property
    def build_dir(self):
        return self.working_dir / "build"

    @cached_property
    def merge_dir(self):
        return self.working_dir / "merge"

    @cached_property
    def trash_dir(self):
        return self.working_dir / "trash"

    @cached_property
    def GLOBAL_LOG_FILE(self):
        log_file = self.converted_dir / "auto-m4b.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.touch(exist_ok=True)
        return log_file

    @cached_property
    def PID_FILE(self):
        pid_file = self.tmp_dir / "running.pid"
        return pid_file

    @cached_property
    def FATAL_FILE(self):
        fatal_file = self.tmp_dir / "fatal.log"
        return fatal_file

    def clean(self):
        from src.lib.fs_utils import clean_dir

        # Pre-clean working folders
        clean_dir(self.merge_dir)
        clean_dir(self.build_dir)
        clean_dir(self.trash_dir)

    def check_dirs(self):

        dirs = [
            self.inbox_dir,
            self.converted_dir,
            self.archive_dir,
            self.backup_dir,
            self.failed_dir,
            self.working_dir,
            self.build_dir,
            self.merge_dir,
            self.trash_dir,
        ]

        for d in dirs:
            ensure_dir_exists_and_is_writable(d)

    def clear_cached_attrs(self):
        for prop in [d for d in dir(self) if not d.startswith("_")]:
            try:
                delattr(self, prop)
            except AttributeError:
                pass

    def check_m4b_tool(self):
        has_native_m4b_tool = bool(shutil.which(self.m4b_tool))
        if has_native_m4b_tool:
            return True

        # docker images -q sandreas/m4b-tool:latest
        has_docker = bool(self.docker_path)
        docker_exe = self.docker_path or "docker"
        docker_image_exists = has_docker and bool(
            subprocess.check_output(
                [docker_exe, "images", "-q", "sandreas/m4b-tool:latest"],
                timeout=10,
            ).strip()
        )
        docker_ready = has_docker and docker_image_exists
        current_version = (
            (
                subprocess.check_output(["m4b-tool", "--version"], timeout=10)
                .decode()
                .strip()
            )
            if not docker_ready
            else (
                subprocess.check_output(
                    [
                        docker_exe,
                        "run",
                        "--rm",
                        "sandreas/m4b-tool:latest",
                        "m4b-tool",
                        "--version",
                    ],
                    timeout=10,
                )
                .decode()
                .strip()
            )
        )
        env_use_docker = bool(
            os.getenv("USE_DOCKER", self.env.get("USE_DOCKER", False))
        )
        install_script = "./scripts/install-docker-m4b-tool.sh"

        if not re.search(r"v0.5", current_version):
            raise RuntimeError(
                f"m4b-tool version {current_version} is not supported, please install v0.5-prerelease (if using Docker, run {install_script} to install the correct version)"
            )

        if docker_ready:
            uid = os.getuid()
            gid = os.getgid()
            is_tty = os.isatty(0)
            # Set the m4b_tool to the docker image
            # create working_dir if it does not exist
            self.working_dir.mkdir(parents=True, exist_ok=True)
            self._m4b_tool = [
                c
                for c in [
                    str(docker_exe),
                    "run",
                    "-it" if is_tty else "",
                    "--rm",
                    "-u",
                    f"{uid}:{gid}",
                    "-v",
                    f"{self.working_dir}:/mnt:rw",
                    "sandreas/m4b-tool:latest",
                ]
                if c
            ]

            self._USE_DOCKER = True
            return True

        elif env_use_docker:
            if not has_docker:
                if self.docker_path:
                    raise RuntimeError(
                        f"Could not find 'docker' executable at {self.docker_path}, please ensure Docker is in your PATH or set DOCKER_PATH to the correct path"
                    )
                raise RuntimeError(
                    f"Could not find 'docker' in PATH, please install Docker and try again, or set USE_DOCKER to N to use the native m4b-tool (if installed)"
                )
            elif not docker_image_exists:
                raise RuntimeError(
                    f"Could not find the image 'sandreas/m4b-tool:latest', run\n\n $ docker pull sandreas/m4b-tool:latest\n  # or\n $ {install_script}\n\nand try again, or set USE_DOCKER to N to use the native m4b-tool (if installed)"
                )
        else:
            raise RuntimeError(
                f"Could not find '{self.m4b_tool}' in PATH, please install it and try again (see https://github.com/sandreas/m4b-tool).\nIf you are using Docker, make sure the image 'sandreas/m4b-tool:latest' is available, and you've aliased `m4b-tool` to run the container.\nFor easy Docker setup, run:\n\n$ {install_script}"
            )

    @contextmanager
    def load_env(self, args: AutoM4bArgs | None = None, *, quiet: bool = False):
        msg = ""
        self._args = args or AutoM4bArgs()

        self.TEST = (
            self._args.test
            if self._args.test is not None
            else (self.TEST or "pytest" in sys.modules)
        )

        if self.args.env:
            if self._dotenv_src != self.args.env:
                msg = f"Loading ENV from {self.args.env}"
            self._dotenv_src = self.args.env
            self._env = load_env(self.args.env)
        elif self.TEST:
            env_file = get_git_root() / ".env.test"
            if self._dotenv_src != env_file:
                msg = f"Loading test ENV from {env_file}"
            self._dotenv_src = env_file
            self._env = load_env(env_file)
        else:
            self._env = {}
        for k, v in self._env.items():
            self.set_env_var(k, v)

        if self.args.match_filter:
            self.MATCH_FILTER = self.args.match_filter

        yield "" if quiet else msg

    @overload
    def load_path_env(
        self, key: str, default: Path, allow_empty: bool = ...
    ) -> Path: ...

    @overload
    def load_path_env(
        self,
        key: str,
        default: Path | None = None,
        allow_empty: Literal[True] = True,
    ) -> Path | None: ...

    @overload
    def load_path_env(
        self,
        key: str,
        default: Path | None = None,
        allow_empty: Literal[False] = False,
    ) -> Path: ...

    def load_path_env(
        self, key: str, default: Path | None = None, allow_empty: bool = True
    ) -> Path | None:
        v = self.get_env_var(key, default=default)
        path = Path(v).expanduser() if v else default
        if not path and not allow_empty:
            raise EnvironmentError(
                f"{key} is not set, please make sure to set it in a .env file or as an ENV var"
            )
        return path.resolve() if path else None

    @overload
    def get_env_var(self, key: str) -> Any | None: ...

    @overload
    def get_env_var(self, key: str, default: D) -> str | D: ...

    def get_env_var(self, key: str, default: D | None = None) -> str | None | D:
        if not self._env:
            with self.load_env(quiet=True):
                ...
        return cast(D, os.getenv(key, self.env.get(key, default)))

    def set_env_var(self, key: str, value: Any):
        typed_value = set_typed_env_var(key, value, self._env)[key]

        if key.upper() == key and not key.startswith("_"):
            setattr(self, key, typed_value)

    def reload(self):
        self.__init__()
        self.clear_cached_attrs()
        self.load_env()

    @staticmethod
    def print_config_help():
        """Print all available configuration options with descriptions."""
        # Import here to avoid circular dependency issues
        try:
            from src.lib.term import print_mint, print_grey
        except:
            # Fallback if term module has issues
            def print_mint(s):
                print(s)
            def print_grey(s):
                print(s)

        print_mint("\n=== Auto-M4B Configuration Options ===\n")

        config_options = [
            ("INBOX_FOLDER", "Path", "Directory to watch for new audiobooks (required)", None),
            ("CONVERTED_FOLDER", "Path", "Directory where converted M4B files are saved (required)", None),
            ("ARCHIVE_FOLDER", "Path", "Directory where original files are archived after conversion (required)", None),
            ("BACKUP_FOLDER", "Path", "Directory where backups are stored (required)", None),
            ("FAILED_FOLDER", "Path", "Directory where failed conversions are moved (required)", None),
            ("WORKING_FOLDER", "Path", "Temporary working directory (default: system temp)", None),
            ("", "", "", ""),
            ("CPU_CORES", "Integer", f"Number of CPU cores to use for conversion (default: {cpu_count()})", cpu_count()),
            ("SLEEP_TIME", "Float", f"Seconds to sleep between loops (default: {DEFAULT_SLEEP_TIME})", DEFAULT_SLEEP_TIME),
            ("WAIT_TIME", "Float", f"Seconds to wait when directory recently modified (default: {DEFAULT_WAIT_TIME})", DEFAULT_WAIT_TIME),
            ("", "", "", ""),
            ("ON_COMPLETE", "String", "What to do after conversion: 'archive', 'delete', or 'test_do_nothing' (default: archive)", "archive"),
            ("OVERWRITE_EXISTING", "Boolean", "Whether to overwrite existing M4B files (default: N)", False),
            ("BACKUP", "Boolean", "Whether to create backups (default: Y)", True),
            ("", "", "", ""),
            ("MAX_RETRIES", "Integer", "Maximum retry attempts for failed books (default: 3)", 3),
            ("RETRY_TRANSIENT_ERRORS", "Boolean", "Automatically retry transient errors (default: Y)", True),
            ("RETRY_BASE_DELAY", "Integer", "Base delay in seconds for exponential backoff (default: 60)", 60),
            ("MOVE_FAILED_BOOKS", "Boolean", "Move books to failed folder after max retries (default: Y)", True),
            ("", "", "", ""),
            ("USE_FILENAMES_AS_CHAPTERS", "Boolean", "Use audio filenames as chapter names (default: N)", False),
            ("FLATTEN_MULTI_DISC_BOOKS", "Boolean", "[Beta] Flatten multi-disc audiobooks into single file (default: N)", False),
            ("CONVERT_SERIES", "Boolean", "[Beta] Convert entire book series as one audiobook (default: N)", False),
            ("", "", "", ""),
            ("AUDIO_EXTS", "String", "Comma-separated list of audio file extensions (default: .mp3,.m4a,.m4b,.wma)", ".mp3,.m4a,.m4b,.wma"),
            ("NO_CATS", "Boolean", "Disable cat ASCII art (default: N)", False),
            ("", "", "", ""),
            ("DEBUG", "Boolean", "Enable debug logging (default: N)", False),
            ("TEST", "Boolean", "Enable test mode (default: N)", False),
        ]

        for var_name, var_type, description, default in config_options:
            if not var_name:  # Empty line for spacing
                print()
                continue

            default_str = f" (default: {default})" if default is not None else ""
            print_grey(f"  {var_name:<30} [{var_type}]")
            print(f"    {description}")

        print_mint("\n=== Docker-Specific Options ===\n")
        print_grey(f"  {'USE_DOCKER':<30} [Boolean]")
        print(f"    Force use of Docker for m4b-tool (auto-detected if not set)")
        print_grey(f"  {'DOCKER_PATH':<30} [Path]")
        print(f"    Path to docker executable (default: auto-detect)")

        print_mint("\n=== Examples ===\n")
        print("  Set via environment variable:")
        print("    export CPU_CORES=4")
        print()
        print("  Set via .env file:")
        print("    CPU_CORES=4")
        print("    MAX_RETRIES=5")
        print()
        print("  Set via docker-compose.yml:")
        print("    environment:")
        print("      - CPU_CORES=4")
        print("      - MAX_RETRIES=5")
        print()

    def validate_config(self) -> tuple[bool, list[str]]:
        """
        Validate the current configuration.

        Returns:
            tuple[bool, list[str]]: (is_valid, list of error messages)
        """
        errors = []

        # Check required directory paths
        required_dirs = [
            ("INBOX_FOLDER", self.inbox_dir),
            ("CONVERTED_FOLDER", self.converted_dir),
            ("ARCHIVE_FOLDER", self.archive_dir),
            ("BACKUP_FOLDER", self.backup_dir),
            ("FAILED_FOLDER", self.failed_dir),
        ]

        for var_name, path in required_dirs:
            if not path:
                errors.append(f"{var_name} is not set or is empty")
            else:
                try:
                    # Check if parent directory exists (we can create the final dir)
                    if not path.parent.exists() and path.parent != path:
                        errors.append(f"{var_name} parent directory does not exist: {path.parent}")
                except Exception as e:
                    errors.append(f"{var_name} is invalid: {e}")

        # Check numeric values
        if self.CPU_CORES <= 0:
            errors.append(f"CPU_CORES must be greater than 0, got: {self.CPU_CORES}")

        if self.CPU_CORES > cpu_count() * 2:
            errors.append(f"CPU_CORES ({self.CPU_CORES}) is much higher than available cores ({cpu_count()}), this may cause performance issues")

        if self.SLEEP_TIME < 0:
            errors.append(f"SLEEP_TIME must be >= 0, got: {self.SLEEP_TIME}")

        if self.WAIT_TIME < 0:
            errors.append(f"WAIT_TIME must be >= 0, got: {self.WAIT_TIME}")

        if self.MAX_RETRIES < 0:
            errors.append(f"MAX_RETRIES must be >= 0, got: {self.MAX_RETRIES}")

        if self.RETRY_BASE_DELAY < 0:
            errors.append(f"RETRY_BASE_DELAY must be >= 0, got: {self.RETRY_BASE_DELAY}")

        # Check ON_COMPLETE value
        valid_on_complete = ["archive", "delete", "test_do_nothing"]
        if self.ON_COMPLETE not in valid_on_complete:
            errors.append(f"ON_COMPLETE must be one of {valid_on_complete}, got: {self.ON_COMPLETE}")

        # Check m4b-tool availability
        try:
            self.check_m4b_tool()
        except Exception as e:
            errors.append(f"m4b-tool check failed: {e}")

        # Check docker if USE_DOCKER is set
        if os.getenv("USE_DOCKER"):
            if not self.docker_path:
                errors.append("USE_DOCKER is set but docker executable not found")

        return (len(errors) == 0, errors)


cfg = Config()

__all__ = ["cfg"]
