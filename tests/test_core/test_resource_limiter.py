"""
Tests for compressy.core.resource_limiter module.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from compressy.core import resource_limiter
from compressy.core.resource_limiter import (
    VALID_IO_PRIORITIES,
    VALID_PROCESS_PRIORITIES,
    apply_io_priority,
    build_popen_kwargs,
    is_linux,
    is_windows,
)


@pytest.mark.unit
class TestPlatformDetection:
    """Tests for the platform detection helpers."""

    def test_is_windows_true(self):
        with patch("compressy.core.resource_limiter.sys") as mock_sys:
            mock_sys.platform = "win32"
            assert is_windows() is True

    def test_is_windows_false(self):
        with patch("compressy.core.resource_limiter.sys") as mock_sys:
            mock_sys.platform = "linux"
            assert is_windows() is False

    def test_is_linux_true(self):
        with patch("compressy.core.resource_limiter.sys") as mock_sys:
            mock_sys.platform = "linux2"
            assert is_linux() is True

    def test_is_linux_false(self):
        with patch("compressy.core.resource_limiter.sys") as mock_sys:
            mock_sys.platform = "darwin"
            assert is_linux() is False


@pytest.mark.unit
class TestBuildPopenKwargs:
    """Tests for build_popen_kwargs."""

    def test_none_priority_returns_empty(self):
        assert build_popen_kwargs(None) == {}

    def test_empty_string_priority_returns_empty(self):
        assert build_popen_kwargs("") == {}

    def test_invalid_priority_returns_empty_and_warns(self):
        logger = MagicMock()
        result = build_popen_kwargs("nonsense", logger=logger)
        assert result == {}
        logger.warning.assert_called_once()

    def test_invalid_priority_no_logger_safe(self):
        # Should not blow up without a logger
        assert build_popen_kwargs("nonsense") == {}

    def test_windows_priority_uses_creationflags(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=True):
            result = build_popen_kwargs("low")
        assert "creationflags" in result
        # IDLE_PRIORITY_CLASS = 0x40
        assert result["creationflags"] == 0x40

    def test_windows_below_normal_uses_correct_flag(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=True):
            result = build_popen_kwargs("below_normal")
        assert result["creationflags"] == 0x4000

    def test_windows_normal_uses_correct_flag(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=True):
            result = build_popen_kwargs("normal")
        assert result["creationflags"] == 0x20

    def test_windows_high_uses_correct_flag(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=True):
            result = build_popen_kwargs("high")
        assert result["creationflags"] == 0x80

    def test_posix_low_uses_preexec_fn(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=False):
            result = build_popen_kwargs("low")
        assert "preexec_fn" in result
        assert callable(result["preexec_fn"])

    def test_posix_normal_returns_empty(self):
        # nice value 0 means do nothing
        with patch("compressy.core.resource_limiter.is_windows", return_value=False):
            result = build_popen_kwargs("normal")
        assert result == {}

    def test_posix_preexec_calls_os_nice(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=False):
            result = build_popen_kwargs("low")
        preexec = result["preexec_fn"]

        # os.nice does not exist on Windows, so use create=True for the patch.
        with patch("compressy.core.resource_limiter.os.nice", create=True) as mock_nice:
            preexec()
            mock_nice.assert_called_once_with(19)

    def test_posix_preexec_swallows_oserror(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=False):
            result = build_popen_kwargs("high")
        preexec = result["preexec_fn"]

        with patch(
            "compressy.core.resource_limiter.os.nice",
            create=True,
            side_effect=PermissionError("denied"),
        ):
            preexec()  # Should not raise

    def test_posix_preexec_swallows_attribute_error(self):
        with patch("compressy.core.resource_limiter.is_windows", return_value=False):
            result = build_popen_kwargs("high")
        preexec = result["preexec_fn"]

        with patch(
            "compressy.core.resource_limiter.os.nice",
            create=True,
            side_effect=AttributeError("no nice"),
        ):
            preexec()  # Should not raise

    def test_valid_priorities_constant_complete(self):
        # Sanity check: the constant matches the keys we map for both platforms
        assert set(VALID_PROCESS_PRIORITIES) >= {"low", "below_normal", "normal", "above_normal", "high"}

    def test_windows_priority_dict_missing_falls_back(self):
        """If the Windows priority table is missing the key the helper returns {}."""
        with patch(
            "compressy.core.resource_limiter._WINDOWS_PRIORITY_CLASSES",
            {},  # empty mapping forces flag=None branch
        ), patch("compressy.core.resource_limiter.is_windows", return_value=True):
            assert build_popen_kwargs("low") == {}


@pytest.mark.unit
class TestApplyIOPriority:
    """Tests for apply_io_priority."""

    def test_no_priority_returns_false(self):
        process = MagicMock()
        assert apply_io_priority(process, None) is False

    def test_empty_priority_returns_false(self):
        process = MagicMock()
        assert apply_io_priority(process, "") is False

    def test_invalid_priority_returns_false_and_warns(self):
        process = MagicMock()
        logger = MagicMock()
        assert apply_io_priority(process, "bogus", logger=logger) is False
        logger.warning.assert_called_once()

    def test_invalid_priority_without_logger(self):
        process = MagicMock()
        assert apply_io_priority(process, "bogus") is False

    def test_unsupported_platform_warns(self):
        process = MagicMock()
        logger = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=False
        ), patch("compressy.core.resource_limiter.sys") as mock_sys:
            mock_sys.platform = "darwin"
            assert apply_io_priority(process, "low", logger=logger) is False
        logger.warning.assert_called()

    def test_unsupported_platform_no_logger(self):
        process = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=False
        ), patch("compressy.core.resource_limiter.sys") as mock_sys:
            mock_sys.platform = "darwin"
            assert apply_io_priority(process, "low") is False

    def test_valid_io_priorities_constant(self):
        assert "idle" in VALID_IO_PRIORITIES
        assert "low" in VALID_IO_PRIORITIES
        assert "normal" in VALID_IO_PRIORITIES
        assert "high" in VALID_IO_PRIORITIES


@pytest.mark.unit
class TestApplyIOPriorityLinux:
    """Tests for the Linux ionice-based code path."""

    def test_linux_ionice_missing(self):
        process = MagicMock()
        logger = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value=None):
            assert apply_io_priority(process, "idle", logger=logger) is False
        logger.warning.assert_called_once()

    def test_linux_ionice_missing_no_logger(self):
        process = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value=None):
            assert apply_io_priority(process, "idle") is False

    def test_linux_ionice_success(self):
        process = MagicMock()
        process.pid = 1234
        completed = MagicMock(returncode=0, stderr="")
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run", return_value=completed
        ) as mock_run:
            assert apply_io_priority(process, "idle") is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "/usr/bin/ionice"
        assert "-c" in call_args
        assert "3" in call_args  # idle class
        assert "-p" in call_args
        assert "1234" in call_args

    def test_linux_ionice_low_class(self):
        process = MagicMock()
        process.pid = 99
        completed = MagicMock(returncode=0, stderr="")
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run", return_value=completed
        ) as mock_run:
            assert apply_io_priority(process, "low") is True
        call_args = mock_run.call_args[0][0]
        # low/normal -> best-effort class 2
        assert "2" in call_args

    def test_linux_ionice_high_class(self):
        process = MagicMock()
        process.pid = 99
        completed = MagicMock(returncode=0, stderr="")
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run", return_value=completed
        ) as mock_run:
            assert apply_io_priority(process, "high") is True
        call_args = mock_run.call_args[0][0]
        # realtime class 1
        assert "1" in call_args

    def test_linux_ionice_nonzero_exit(self):
        process = MagicMock()
        process.pid = 99
        completed = MagicMock(returncode=1, stderr="boom")
        logger = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run", return_value=completed
        ):
            assert apply_io_priority(process, "idle", logger=logger) is False
        logger.warning.assert_called_once()

    def test_linux_ionice_nonzero_exit_no_logger(self):
        process = MagicMock()
        process.pid = 99
        completed = MagicMock(returncode=1, stderr="boom")
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run", return_value=completed
        ):
            assert apply_io_priority(process, "idle") is False

    def test_linux_ionice_raises_oserror(self):
        process = MagicMock()
        process.pid = 99
        logger = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run",
            side_effect=OSError("blocked"),
        ):
            assert apply_io_priority(process, "idle", logger=logger) is False
        logger.warning.assert_called_once()

    def test_linux_ionice_subprocess_error(self):
        process = MagicMock()
        process.pid = 99
        with patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch("compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"), patch(
            "compressy.core.resource_limiter.subprocess.run",
            side_effect=subprocess.SubprocessError("oops"),
        ):
            assert apply_io_priority(process, "idle") is False

    def test_linux_io_class_dict_missing_falls_back(self):
        """If the ionice class table is empty the helper returns False without invoking subprocess."""
        process = MagicMock()
        process.pid = 99
        with patch(
            "compressy.core.resource_limiter._LINUX_IO_CLASSES",
            {},  # empty mapping forces io_class=None branch
        ), patch("compressy.core.resource_limiter.is_windows", return_value=False), patch(
            "compressy.core.resource_limiter.is_linux", return_value=True
        ), patch(
            "compressy.core.resource_limiter.shutil.which", return_value="/usr/bin/ionice"
        ), patch(
            "compressy.core.resource_limiter.subprocess.run"
        ) as mock_run:
            assert apply_io_priority(process, "idle") is False
        mock_run.assert_not_called()


@pytest.mark.unit
class TestApplyIOPriorityWindows:
    """Tests for the Windows background-mode code path."""

    def _make_kernel32(self, open_handle: int = 1234, set_priority_ok: int = 1):
        kernel32 = MagicMock()
        kernel32.OpenProcess.return_value = open_handle
        kernel32.SetPriorityClass.return_value = set_priority_ok
        return kernel32

    def test_windows_high_priority_skipped_with_debug(self):
        process = MagicMock()
        process.pid = 1
        logger = MagicMock()
        with patch("compressy.core.resource_limiter.is_windows", return_value=True):
            assert apply_io_priority(process, "high", logger=logger) is False
        logger.debug.assert_called()

    def test_windows_high_priority_skipped_no_logger(self):
        process = MagicMock()
        process.pid = 1
        with patch("compressy.core.resource_limiter.is_windows", return_value=True):
            assert apply_io_priority(process, "high") is False

    def test_windows_idle_priority_success(self):
        process = MagicMock()
        process.pid = 1234
        kernel32 = self._make_kernel32(open_handle=999, set_priority_ok=1)

        windll_mock = MagicMock()
        windll_mock.kernel32 = kernel32
        ctypes_mock = MagicMock()
        ctypes_mock.windll = windll_mock

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "idle") is True
        kernel32.OpenProcess.assert_called_once()
        kernel32.SetPriorityClass.assert_called_once()
        kernel32.CloseHandle.assert_called_once_with(999)

    def test_windows_low_priority_uses_background_begin(self):
        process = MagicMock()
        process.pid = 7
        kernel32 = self._make_kernel32()

        ctypes_mock = MagicMock()
        ctypes_mock.windll.kernel32 = kernel32

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "low") is True
        # Verify the second SetPriorityClass argument matches the documented constant
        args, _ = kernel32.SetPriorityClass.call_args
        assert args[1] == 0x00100000  # PROCESS_MODE_BACKGROUND_BEGIN

    def test_windows_open_process_fails(self):
        process = MagicMock()
        process.pid = 1
        kernel32 = self._make_kernel32(open_handle=0)
        logger = MagicMock()

        ctypes_mock = MagicMock()
        ctypes_mock.windll.kernel32 = kernel32

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "idle", logger=logger) is False
        kernel32.SetPriorityClass.assert_not_called()
        logger.warning.assert_called_once()

    def test_windows_open_process_fails_no_logger(self):
        process = MagicMock()
        process.pid = 1
        kernel32 = self._make_kernel32(open_handle=0)

        ctypes_mock = MagicMock()
        ctypes_mock.windll.kernel32 = kernel32

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "idle") is False

    def test_windows_set_priority_fails(self):
        process = MagicMock()
        process.pid = 1
        kernel32 = self._make_kernel32(open_handle=42, set_priority_ok=0)
        logger = MagicMock()

        ctypes_mock = MagicMock()
        ctypes_mock.windll.kernel32 = kernel32

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "idle", logger=logger) is False
        kernel32.CloseHandle.assert_called_once_with(42)
        logger.warning.assert_called_once()

    def test_windows_ctypes_oserror(self):
        process = MagicMock()
        process.pid = 1
        logger = MagicMock()

        ctypes_mock = MagicMock()
        ctypes_mock.windll.kernel32.OpenProcess.side_effect = OSError("nope")

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "idle", logger=logger) is False
        logger.warning.assert_called_once()

    def test_windows_ctypes_attribute_error(self):
        process = MagicMock()
        process.pid = 1

        # ctypes import raises AttributeError when accessing windll on non-windows ctypes
        # Simulate by raising AttributeError from OpenProcess
        ctypes_mock = MagicMock()
        ctypes_mock.windll.kernel32.OpenProcess.side_effect = AttributeError("no windll")

        with patch("compressy.core.resource_limiter.is_windows", return_value=True), patch.dict(
            "sys.modules", {"ctypes": ctypes_mock}
        ):
            assert apply_io_priority(process, "idle") is False


@pytest.mark.unit
class TestModuleConstants:
    """Sanity tests to ensure the module exposes the expected constants."""

    def test_valid_process_priorities_tuple(self):
        assert isinstance(VALID_PROCESS_PRIORITIES, tuple)
        assert "low" in VALID_PROCESS_PRIORITIES
        assert "high" in VALID_PROCESS_PRIORITIES

    def test_valid_io_priorities_tuple(self):
        assert isinstance(VALID_IO_PRIORITIES, tuple)
        assert set(VALID_IO_PRIORITIES) == {"idle", "low", "normal", "high"}

    def test_module_callables_exist(self):
        assert callable(resource_limiter.build_popen_kwargs)
        assert callable(resource_limiter.apply_io_priority)
