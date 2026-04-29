"""
Resource limiting helpers for FFmpeg subprocess execution.

This module centralizes platform-aware logic for constraining the CPU and I/O
footprint of FFmpeg child processes. It is intentionally dependency free
(uses only the standard library) and falls back to safe no-ops on platforms
that do not support a given control. Each public helper documents the
platforms it supports and how it degrades.
"""

import os
import shutil
import subprocess  # nosec B404
import sys
from typing import Any, Callable, Dict, Optional, cast


# ============================================================================
# Constants
# ============================================================================


VALID_PROCESS_PRIORITIES = (
    "low",
    "below_normal",
    "normal",
    "above_normal",
    "high",
)

VALID_IO_PRIORITIES = (
    "idle",
    "low",
    "normal",
    "high",
)


# Windows priority class flags from <winbase.h>. Constants are duplicated here
# instead of importing from subprocess because not every constant is exposed
# on all Python versions.
_WINDOWS_PRIORITY_CLASSES: Dict[str, int] = {
    "low": 0x00000040,  # IDLE_PRIORITY_CLASS
    "below_normal": 0x00004000,  # BELOW_NORMAL_PRIORITY_CLASS
    "normal": 0x00000020,  # NORMAL_PRIORITY_CLASS
    "above_normal": 0x00008000,  # ABOVE_NORMAL_PRIORITY_CLASS
    "high": 0x00000080,  # HIGH_PRIORITY_CLASS
}


# Windows process mode flags used to push a process into background I/O mode
# which lowers I/O priority on Vista+ (only valid for the current process,
# but SetPriorityClass on a child handle works as well).
_WINDOWS_BACKGROUND_BEGIN = 0x00100000  # PROCESS_MODE_BACKGROUND_BEGIN
_WINDOWS_BACKGROUND_END = 0x00200000  # PROCESS_MODE_BACKGROUND_END


# Mapping from semantic priority name to a POSIX nice increment. Higher nice
# values mean lower CPU priority; negative values require elevated privileges
# and are best-effort only.
_POSIX_NICE_VALUES: Dict[str, int] = {
    "low": 19,
    "below_normal": 10,
    "normal": 0,
    "above_normal": -5,
    "high": -10,
}


# Linux ionice classes: 1=realtime, 2=best-effort, 3=idle.
_LINUX_IO_CLASSES: Dict[str, str] = {
    "idle": "3",
    "low": "2",
    "normal": "2",
    "high": "1",
}


# ============================================================================
# Platform Detection
# ============================================================================


def is_windows() -> bool:
    """Return True if running on Windows."""
    return sys.platform == "win32"


def is_linux() -> bool:
    """Return True if running on Linux."""
    return sys.platform.startswith("linux")


# ============================================================================
# Popen kwargs construction
# ============================================================================


def build_popen_kwargs(
    process_priority: Optional[str],
    logger: Any = None,
) -> Dict[str, Any]:
    """
    Build platform-appropriate kwargs to pass to ``subprocess.Popen`` so the
    new FFmpeg child process starts with the requested priority.

    Args:
        process_priority: Semantic priority name (see VALID_PROCESS_PRIORITIES)
            or ``None`` to leave the default behavior unchanged.
        logger: Optional logger used to report platform fallbacks.

    Returns:
        Dictionary of kwargs to merge into the ``Popen`` call. Returns an
        empty dict when no platform-safe action is available.
    """
    if not process_priority:
        return {}

    if process_priority not in VALID_PROCESS_PRIORITIES:
        if logger:
            logger.warning(f"Unknown process priority '{process_priority}', skipping")
        return {}

    if is_windows():
        flag = _WINDOWS_PRIORITY_CLASSES.get(process_priority)
        if flag is None:
            return {}
        return {"creationflags": flag}

    nice_value = _POSIX_NICE_VALUES.get(process_priority)
    if nice_value is None or nice_value == 0:
        return {}

    return {"preexec_fn": _make_nice_preexec(nice_value)}


def _make_nice_preexec(nice_value: int) -> Callable[[], None]:
    """Create a preexec_fn that adjusts niceness, swallowing failures."""

    def _apply_nice() -> None:
        try:
            nice_fn = cast(Callable[[int], int], getattr(os, "nice"))
            nice_fn(nice_value)
        except (OSError, AttributeError, PermissionError):
            # nice() is unavailable on Windows, and negative increments require
            # CAP_SYS_NICE on POSIX. Fall back silently rather than fail the
            # entire FFmpeg launch over a soft preference.
            pass

    return _apply_nice


# ============================================================================
# Post-launch I/O priority application
# ============================================================================


def apply_io_priority(
    process: "subprocess.Popen[Any]",
    io_priority: Optional[str],
    logger: Any = None,
) -> bool:
    """
    Best-effort application of I/O priority to an already-launched process.

    Args:
        process: The already-launched ``Popen`` instance for FFmpeg.
        io_priority: One of ``VALID_IO_PRIORITIES`` or ``None``.
        logger: Optional logger used to report platform fallbacks.

    Returns:
        True if a platform-specific change was successfully applied, False
        otherwise (including when no priority was requested).
    """
    if not io_priority:
        return False

    if io_priority not in VALID_IO_PRIORITIES:
        if logger:
            logger.warning(f"Unknown io priority '{io_priority}', skipping")
        return False

    if is_windows():
        return _apply_windows_io_priority(process, io_priority, logger)

    if is_linux():
        return _apply_linux_io_priority(process, io_priority, logger)

    if logger:
        logger.warning(f"I/O priority not supported on platform '{sys.platform}'")
    return False


def _apply_windows_io_priority(
    process: "subprocess.Popen[Any]",
    io_priority: str,
    logger: Any = None,
) -> bool:
    """Apply background-mode I/O priority on Windows when requested.

    Windows only exposes a coarse mechanism for child I/O priority via
    ``PROCESS_MODE_BACKGROUND_BEGIN``. We use it for ``idle``/``low`` and
    leave ``normal``/``high`` alone (no native API for raising I/O priority
    without administrative privileges).
    """
    if io_priority not in ("idle", "low"):
        if logger:
            logger.debug(f"Skipping Windows I/O priority for '{io_priority}' " "(only idle/low are supported)")
        return False

    try:
        import ctypes  # local import: only needed on Windows

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        PROCESS_SET_INFORMATION = 0x0200
        handle = kernel32.OpenProcess(PROCESS_SET_INFORMATION, False, process.pid)
        if not handle:
            if logger:
                logger.warning(f"Could not open FFmpeg process for I/O priority change " f"(pid={process.pid})")
            return False
        try:
            ok = kernel32.SetPriorityClass(handle, _WINDOWS_BACKGROUND_BEGIN)
            if not ok and logger:
                logger.warning(f"SetPriorityClass background-begin failed for pid={process.pid}")
            return bool(ok)
        finally:
            kernel32.CloseHandle(handle)
    except (OSError, AttributeError, ImportError) as exc:
        if logger:
            logger.warning(f"Failed to apply Windows I/O priority: {exc}")
        return False


def _apply_linux_io_priority(
    process: "subprocess.Popen[Any]",
    io_priority: str,
    logger: Any = None,
) -> bool:
    """Use ``ionice`` to adjust I/O priority of the FFmpeg child on Linux."""
    ionice_path = shutil.which("ionice")
    if not ionice_path:
        if logger:
            logger.warning("I/O priority requested but 'ionice' is not available in PATH")
        return False

    io_class = _LINUX_IO_CLASSES.get(io_priority)
    if io_class is None:
        return False

    try:
        result = subprocess.run(  # nosec B603
            [ionice_path, "-c", io_class, "-p", str(process.pid)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if logger:
                logger.warning(f"ionice exited {result.returncode} for pid={process.pid}: " f"{result.stderr.strip()}")
            return False
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        if logger:
            logger.warning(f"Failed to invoke ionice: {exc}")
        return False
