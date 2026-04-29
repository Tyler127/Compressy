import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from compressy.core.resource_limiter import (
    VALID_IO_PRIORITIES,
    VALID_PROCESS_PRIORITIES,
)


# ============================================================================
# Configuration Classes
# ============================================================================


@dataclass
class LoggingConfig:
    """Configuration for logging system."""

    log_level: str = "INFO"
    log_dir: str = "logs"
    enable_console: bool = True
    enable_file: bool = True
    rotation_enabled: bool = False
    rotation_type: str = "size"
    max_bytes: int = 10485760  # 10 MB
    backup_count: int = 5
    when: str = "midnight"

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "LoggingConfig":
        """
        Create LoggingConfig from dictionary.

        Args:
            config_dict: Dictionary with logging configuration

        Returns:
            LoggingConfig instance
        """
        rotation_config = config_dict.get("rotation", {})
        return cls(
            log_level=config_dict.get("log_level", "INFO"),
            log_dir=config_dict.get("log_dir", "logs"),
            enable_console=config_dict.get("enable_console", True),
            enable_file=config_dict.get("enable_file", True),
            rotation_enabled=rotation_config.get("enabled", False),
            rotation_type=rotation_config.get("type", "size"),
            max_bytes=rotation_config.get("max_bytes", 10485760),
            backup_count=rotation_config.get("backup_count", 5),
            when=rotation_config.get("when", "midnight"),
        )

    @classmethod
    def load_from_file(cls, config_path: Path) -> "LoggingConfig":
        """
        Load logging configuration from JSON file.

        Args:
            config_path: Path to logging configuration JSON file

        Returns:
            LoggingConfig instance with loaded settings
        """
        if not config_path.exists():
            return cls()  # Return default configuration

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load logging config from {config_path}: {e}")
            return cls()  # Return default configuration

    def merge_with_cli_args(self, log_level: Optional[str] = None, log_dir: Optional[str] = None) -> "LoggingConfig":
        """
        Merge configuration with CLI arguments. CLI args take precedence.

        Args:
            log_level: Log level from CLI
            log_dir: Log directory from CLI

        Returns:
            New LoggingConfig with merged settings
        """
        return LoggingConfig(
            log_level=log_level if log_level is not None else self.log_level,
            log_dir=log_dir if log_dir is not None else self.log_dir,
            enable_console=self.enable_console,
            enable_file=self.enable_file,
            rotation_enabled=self.rotation_enabled,
            rotation_type=self.rotation_type,
            max_bytes=self.max_bytes,
            backup_count=self.backup_count,
            when=self.when,
        )


@dataclass
class CompressionConfig:
    """Configuration for media compression."""

    source_folder: Path
    video_crf: int = 23
    video_preset: str = "medium"
    video_resize: Optional[int] = None
    image_quality: int = 100
    image_resize: Optional[int] = None
    recursive: bool = False
    overwrite: bool = False
    ffmpeg_path: Optional[str] = None
    progress_interval: float = 5.0
    keep_if_larger: bool = False
    backup_dir: Optional[Path] = None
    preserve_format: bool = False
    preserve_timestamps: bool = False
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    output_dir: Optional[Path] = None
    video_resolution: Optional[str] = None
    auto_rename_duplicates: bool = True
    ffmpeg_threads: Optional[int] = None
    ffmpeg_process_priority: Optional[str] = None
    ffmpeg_io_priority: Optional[str] = None
    cooldown_seconds: float = 0.0


# ============================================================================
# Parameter Validator
# ============================================================================


class ParameterValidator:
    """Validates compression parameters."""

    @staticmethod
    def validate(config: CompressionConfig) -> None:
        """Validate all parameters in the configuration."""
        ParameterValidator.validate_video_crf(config.video_crf)
        ParameterValidator.validate_image_quality(config.image_quality)
        ParameterValidator.validate_video_preset(config.video_preset)
        ParameterValidator.validate_video_resize(config.video_resize)
        ParameterValidator.validate_image_resize(config.image_resize)
        ParameterValidator.validate_size_range(config.min_size, config.max_size)
        ParameterValidator.validate_output_dir(config.output_dir, config.overwrite, config.source_folder)
        ParameterValidator.validate_video_resolution(config.video_resolution)
        ParameterValidator.validate_video_resize_and_resolution(config.video_resize, config.video_resolution)
        ParameterValidator.validate_ffmpeg_threads(config.ffmpeg_threads)
        ParameterValidator.validate_ffmpeg_process_priority(config.ffmpeg_process_priority)
        ParameterValidator.validate_ffmpeg_io_priority(config.ffmpeg_io_priority)
        ParameterValidator.validate_cooldown_seconds(config.cooldown_seconds)

    @staticmethod
    def validate_video_crf(video_crf: int) -> None:
        """Validate video CRF value."""
        if not (0 <= video_crf <= 51):
            raise ValueError(f"video_crf must be between 0 and 51, got {video_crf}")

    @staticmethod
    def validate_image_quality(image_quality: int) -> None:
        """Validate image quality value."""
        if not (0 <= image_quality <= 100):
            raise ValueError(f"image_quality must be between 0 and 100, got {image_quality}")

    @staticmethod
    def validate_video_preset(video_preset: str) -> None:
        """Validate video preset."""
        valid_presets = [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ]
        if video_preset not in valid_presets:
            raise ValueError(f"video_preset must be one of {valid_presets}, got {video_preset}")

    @staticmethod
    def validate_video_resize(video_resize: Optional[int]) -> None:
        """Validate video resize value."""
        if video_resize is not None and not (0 <= video_resize <= 100):
            raise ValueError(f"video_resize must be between 0 and 100, got {video_resize}")

    @staticmethod
    def validate_image_resize(image_resize: Optional[int]) -> None:
        """Validate image resize value."""
        if image_resize is not None and not (1 <= image_resize <= 100):
            raise ValueError(f"image_resize must be between 1 and 100, got {image_resize}")

    @staticmethod
    def validate_size_range(min_size: Optional[int], max_size: Optional[int]) -> None:
        """Validate min_size and max_size values."""
        if min_size is not None and min_size < 0:
            raise ValueError(f"min_size must be non-negative, got {min_size}")
        if max_size is not None and max_size < 0:
            raise ValueError(f"max_size must be non-negative, got {max_size}")
        if min_size is not None and max_size is not None and min_size > max_size:
            raise ValueError(f"min_size ({min_size}) cannot be greater than max_size ({max_size})")

    @staticmethod
    def validate_output_dir(output_dir: Optional[Path], overwrite: bool, source_folder: Path) -> None:
        """Validate output directory configuration."""
        if output_dir is not None and overwrite:
            raise ValueError("Cannot use --output-dir and --overwrite together. Choose one.")
        if output_dir is not None and source_folder.resolve() == output_dir.resolve():
            raise ValueError("output_dir cannot be the same as source_folder")

    @staticmethod
    def validate_video_resolution(video_resolution: Optional[str]) -> None:
        """Validate video resolution format."""
        if video_resolution is None:
            return

        # Import parse_resolution to validate
        from compressy.utils.format import parse_resolution

        try:
            parse_resolution(video_resolution)
        except ValueError as e:
            raise ValueError(f"Invalid video resolution: {e}")

    @staticmethod
    def validate_video_resize_and_resolution(video_resize: Optional[int], video_resolution: Optional[str]) -> None:
        """Validate that video_resize and video_resolution are not used together."""
        if video_resize is not None and video_resolution is not None:
            raise ValueError(
                "Cannot use --video-resize and --video-resolution together. "
                "Choose one: use --video-resize for proportional scaling or --video-resolution for fixed dimensions."
            )

    @staticmethod
    def validate_ffmpeg_threads(ffmpeg_threads: Optional[int]) -> None:
        """Validate FFmpeg thread count.

        ``None`` means "do not pass ``-threads``" and keeps the default
        FFmpeg behavior. A value of ``0`` is the FFmpeg-recognized "auto"
        signal. Positive integers cap concurrent encode threads.
        """
        if ffmpeg_threads is None:
            return
        if not isinstance(ffmpeg_threads, int) or isinstance(ffmpeg_threads, bool):
            raise ValueError(f"ffmpeg_threads must be an integer, got {type(ffmpeg_threads).__name__}")
        if ffmpeg_threads < 0:
            raise ValueError(f"ffmpeg_threads must be non-negative (0 = auto), got {ffmpeg_threads}")
        if ffmpeg_threads > 64:
            raise ValueError(f"ffmpeg_threads must be 64 or fewer to avoid runaway thread counts, got {ffmpeg_threads}")

    @staticmethod
    def validate_ffmpeg_process_priority(process_priority: Optional[str]) -> None:
        """Validate FFmpeg process priority value."""
        if process_priority is None:
            return
        if process_priority not in VALID_PROCESS_PRIORITIES:
            raise ValueError(
                f"ffmpeg_process_priority must be one of {list(VALID_PROCESS_PRIORITIES)}, got {process_priority}"
            )

    @staticmethod
    def validate_ffmpeg_io_priority(io_priority: Optional[str]) -> None:
        """Validate FFmpeg I/O priority value."""
        if io_priority is None:
            return
        if io_priority not in VALID_IO_PRIORITIES:
            raise ValueError(
                f"ffmpeg_io_priority must be one of {list(VALID_IO_PRIORITIES)}, got {io_priority}"
            )

    @staticmethod
    def validate_cooldown_seconds(cooldown_seconds: float) -> None:
        """Validate cooldown delay between files."""
        if cooldown_seconds is None:
            raise ValueError("cooldown_seconds must be a number, got None")
        if isinstance(cooldown_seconds, bool):
            raise ValueError(f"cooldown_seconds must be a number, got {type(cooldown_seconds).__name__}")
        if not isinstance(cooldown_seconds, (int, float)):
            raise ValueError(f"cooldown_seconds must be a number, got {type(cooldown_seconds).__name__}")
        if cooldown_seconds < 0:
            raise ValueError(f"cooldown_seconds must be non-negative, got {cooldown_seconds}")
