import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from compressy.utils.format import format_size


# ============================================================================
# Statistics Tracker
# ============================================================================


class StatisticsTracker:
    """Tracks compression statistics."""

    def __init__(self, recursive: bool = False):
        """
        Initialize statistics tracker.

        Args:
            recursive: Whether to track per-folder statistics
        """
        self.recursive = recursive
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "errors": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "space_saved": 0,
            "files": [],
            # Type-level statistics
            "videos_processed": 0,
            "images_processed": 0,
            "videos_skipped": 0,
            "images_skipped": 0,
            "videos_errors": 0,
            "images_errors": 0,
            "videos_original_size": 0,
            "videos_compressed_size": 0,
            "videos_space_saved": 0,
            "images_original_size": 0,
            "images_compressed_size": 0,
            "images_space_saved": 0,
            # Format-level statistics
            "format_stats": {},
        }

        if recursive:
            self.stats["folder_stats"] = {}

    def initialize_folder_stats(self, folder_key: str) -> None:
        """Initialize statistics for a folder."""
        if self.recursive and folder_key not in self.stats["folder_stats"]:
            self.stats["folder_stats"][folder_key] = {
                "total_files": 0,
                "processed": 0,
                "skipped": 0,
                "errors": 0,
                "total_original_size": 0,
                "total_compressed_size": 0,
                "space_saved": 0,
                "files": [],
                # Type-level statistics
                "videos_processed": 0,
                "images_processed": 0,
                "videos_skipped": 0,
                "images_skipped": 0,
                "videos_errors": 0,
                "images_errors": 0,
                "videos_original_size": 0,
                "videos_compressed_size": 0,
                "videos_space_saved": 0,
                "images_original_size": 0,
                "images_compressed_size": 0,
                "images_space_saved": 0,
                # Format-level statistics
                "format_stats": {},
            }

    def add_file_info(self, file_info: Dict, folder_key: str = "root") -> None:
        """
        Add file information to statistics.

        Args:
            file_info: Dictionary with file information
            folder_key: Folder key for recursive mode
        """
        self.stats["files"].append(file_info)

        if self.recursive:
            self.initialize_folder_stats(folder_key)
            self.stats["folder_stats"][folder_key]["files"].append(file_info)

    def _initialize_format_stats(self, format_stats: Dict, extension: str) -> None:
        """Initialize format statistics for a given extension if not exists."""
        if extension not in format_stats:
            format_stats[extension] = {
                "count": 0,
                "original_size": 0,
                "compressed_size": 0,
                "space_saved": 0,
            }

    def update_stats(
        self,
        original_size: int,
        compressed_size: int,
        space_saved: int,
        status: str,
        folder_key: str = "root",
        file_type: Optional[str] = None,
        file_extension: Optional[str] = None,
    ) -> None:
        """
        Update statistics with file processing results.

        Args:
            original_size: Original file size
            compressed_size: Compressed file size
            space_saved: Space saved
            status: Processing status ("processed", "skipped", "error")
            folder_key: Folder key for recursive mode
            file_type: File type ("video" or "image")
            file_extension: File extension without dot (e.g., "mp4", "jpg")
        """
        # Update format stats if extension provided
        if file_extension:
            self._initialize_format_stats(self.stats["format_stats"], file_extension)
            format_stat = self.stats["format_stats"][file_extension]

            if status == "processed":
                format_stat["count"] += 1
                format_stat["original_size"] += original_size
                format_stat["compressed_size"] += compressed_size
                format_stat["space_saved"] += space_saved
            elif status == "skipped":
                format_stat["count"] += 1
                format_stat["original_size"] += original_size
                format_stat["compressed_size"] += compressed_size
            # Note: errors don't add to format stats

        if status == "processed":
            self.stats["processed"] += 1
            self.stats["total_compressed_size"] += compressed_size
            self.stats["space_saved"] += space_saved

            # Update type-level stats
            if file_type == "video":
                self.stats["videos_processed"] += 1
                self.stats["videos_original_size"] += original_size
                self.stats["videos_compressed_size"] += compressed_size
                self.stats["videos_space_saved"] += space_saved
            elif file_type == "image":
                self.stats["images_processed"] += 1
                self.stats["images_original_size"] += original_size
                self.stats["images_compressed_size"] += compressed_size
                self.stats["images_space_saved"] += space_saved

            if self.recursive:
                self.initialize_folder_stats(folder_key)
                folder_stat = self.stats["folder_stats"][folder_key]
                folder_stat["processed"] += 1
                folder_stat["total_compressed_size"] += compressed_size
                folder_stat["space_saved"] += space_saved

                # Update type-level stats for folder
                if file_type == "video":
                    folder_stat["videos_processed"] += 1
                    folder_stat["videos_original_size"] += original_size
                    folder_stat["videos_compressed_size"] += compressed_size
                    folder_stat["videos_space_saved"] += space_saved
                elif file_type == "image":
                    folder_stat["images_processed"] += 1
                    folder_stat["images_original_size"] += original_size
                    folder_stat["images_compressed_size"] += compressed_size
                    folder_stat["images_space_saved"] += space_saved

                # Update format stats for folder
                if file_extension:
                    self._initialize_format_stats(folder_stat["format_stats"], file_extension)
                    folder_format_stat = folder_stat["format_stats"][file_extension]
                    folder_format_stat["count"] += 1
                    folder_format_stat["original_size"] += original_size
                    folder_format_stat["compressed_size"] += compressed_size
                    folder_format_stat["space_saved"] += space_saved

        elif status == "skipped":
            self.stats["skipped"] += 1
            self.stats["total_compressed_size"] += compressed_size

            # Update type-level stats
            if file_type == "video":
                self.stats["videos_skipped"] += 1
                self.stats["videos_original_size"] += original_size
                self.stats["videos_compressed_size"] += compressed_size
            elif file_type == "image":
                self.stats["images_skipped"] += 1
                self.stats["images_original_size"] += original_size
                self.stats["images_compressed_size"] += compressed_size

            if self.recursive:
                self.initialize_folder_stats(folder_key)
                folder_stat = self.stats["folder_stats"][folder_key]
                folder_stat["skipped"] += 1
                folder_stat["total_compressed_size"] += compressed_size

                # Update type-level stats for folder
                if file_type == "video":
                    folder_stat["videos_skipped"] += 1
                    folder_stat["videos_original_size"] += original_size
                    folder_stat["videos_compressed_size"] += compressed_size
                elif file_type == "image":
                    folder_stat["images_skipped"] += 1
                    folder_stat["images_original_size"] += original_size
                    folder_stat["images_compressed_size"] += compressed_size

                # Update format stats for folder
                if file_extension:
                    self._initialize_format_stats(folder_stat["format_stats"], file_extension)
                    folder_format_stat = folder_stat["format_stats"][file_extension]
                    folder_format_stat["count"] += 1
                    folder_format_stat["original_size"] += original_size
                    folder_format_stat["compressed_size"] += compressed_size

        elif status == "error":
            self.stats["errors"] += 1

            # Update type-level stats
            if file_type == "video":
                self.stats["videos_errors"] += 1
            elif file_type == "image":
                self.stats["images_errors"] += 1

            if self.recursive:
                self.initialize_folder_stats(folder_key)
                folder_stat = self.stats["folder_stats"][folder_key]
                folder_stat["errors"] += 1

                # Update type-level stats for folder
                if file_type == "video":
                    folder_stat["videos_errors"] += 1
                elif file_type == "image":
                    folder_stat["images_errors"] += 1

    def add_total_file(self, original_size: int, folder_key: str = "root") -> None:
        """Add a file to total count."""
        self.stats["total_files"] += 1
        self.stats["total_original_size"] += original_size

        if self.recursive:
            self.initialize_folder_stats(folder_key)
            self.stats["folder_stats"][folder_key]["total_files"] += 1
            self.stats["folder_stats"][folder_key]["total_original_size"] += original_size

    def add_total_file_size(self, original_size: int, folder_key: str = "root") -> None:
        """Add file size to total (but don't increment global total_files counter).

        Note: In recursive mode, this DOES increment folder-level total_files
        to ensure per-folder reports are generated correctly.
        """
        self.stats["total_original_size"] += original_size

        if self.recursive:
            self.initialize_folder_stats(folder_key)
            self.stats["folder_stats"][folder_key]["total_files"] += 1
            self.stats["folder_stats"][folder_key]["total_original_size"] += original_size

    def set_total_processing_time(self, total_time: float) -> None:
        """Set total processing time."""
        self.stats["total_processing_time"] = total_time

    def get_stats(self) -> Dict:
        """Get all statistics."""
        return self.stats


# ============================================================================
# Statistics Manager
# ============================================================================


class StatisticsManager:
    """Manages cumulative compression statistics and run history."""

    def __init__(self, statistics_dir: Path):
        """
        Initialize statistics manager.

        Args:
            statistics_dir: Path to the statistics directory
        """
        self.statistics_dir = statistics_dir
        self.statistics_dir.mkdir(parents=True, exist_ok=True)
        self.cumulative_stats_file = self.statistics_dir / "statistics.json"
        self.run_history_file = self.statistics_dir / "run_history.json"
        self.files_log_file = self.statistics_dir / "files.json"

    def load_cumulative_stats(self) -> Dict:
        """
        Load existing cumulative statistics from JSON file.

        Returns:
            Dictionary with cumulative statistics, or defaults if file doesn't exist
        """
        default_stats = {
            "total_runs": 0,
            "total_files_processed": 0,
            "total_files_skipped": 0,
            "total_files_errors": 0,
            "total_original_size_bytes": 0,
            "total_compressed_size_bytes": 0,
            "total_space_saved_bytes": 0,
            # Type-level statistics
            "total_videos_processed": 0,
            "total_images_processed": 0,
            "total_videos_skipped": 0,
            "total_images_skipped": 0,
            "total_videos_errors": 0,
            "total_images_errors": 0,
            "total_videos_original_size_bytes": 0,
            "total_videos_compressed_size_bytes": 0,
            "total_videos_space_saved_bytes": 0,
            "total_images_original_size_bytes": 0,
            "total_images_compressed_size_bytes": 0,
            "total_images_space_saved_bytes": 0,
            # Format statistics (stored as nested dict)
            "format_stats": {},
            "last_updated": None,
        }

        if not self.cumulative_stats_file.exists():
            return default_stats

        try:
            with open(self.cumulative_stats_file, "r", encoding="utf-8") as f:
                stats = json.load(f)
                
                # Ensure all required fields exist with defaults
                for key, default_value in default_stats.items():
                    if key not in stats:
                        stats[key] = default_value
                
                return stats
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Error reading statistics file ({e}). Creating new file.")
            return default_stats
        except Exception as e:
            print(f"Warning: Unexpected error reading statistics file ({e}). Creating new file.")
            return default_stats

    def update_cumulative_stats(self, run_stats: Dict) -> None:
        """
        Update cumulative statistics with current run results.

        Args:
            run_stats: Statistics dictionary from current compression run
        """
        cumulative = self.load_cumulative_stats()

        # Update cumulative totals
        cumulative["total_runs"] += 1
        cumulative["total_files_processed"] += run_stats.get("processed", 0)
        cumulative["total_files_skipped"] += run_stats.get("skipped", 0)
        cumulative["total_files_errors"] += run_stats.get("errors", 0)
        cumulative["total_original_size_bytes"] += run_stats.get("total_original_size", 0)
        cumulative["total_compressed_size_bytes"] += run_stats.get("total_compressed_size", 0)
        cumulative["total_space_saved_bytes"] += run_stats.get("space_saved", 0)

        # Update type-level statistics
        cumulative["total_videos_processed"] += run_stats.get("videos_processed", 0)
        cumulative["total_images_processed"] += run_stats.get("images_processed", 0)
        cumulative["total_videos_skipped"] += run_stats.get("videos_skipped", 0)
        cumulative["total_images_skipped"] += run_stats.get("images_skipped", 0)
        cumulative["total_videos_errors"] += run_stats.get("videos_errors", 0)
        cumulative["total_images_errors"] += run_stats.get("images_errors", 0)
        cumulative["total_videos_original_size_bytes"] += run_stats.get("videos_original_size", 0)
        cumulative["total_videos_compressed_size_bytes"] += run_stats.get("videos_compressed_size", 0)
        cumulative["total_videos_space_saved_bytes"] += run_stats.get("videos_space_saved", 0)
        cumulative["total_images_original_size_bytes"] += run_stats.get("images_original_size", 0)
        cumulative["total_images_compressed_size_bytes"] += run_stats.get("images_compressed_size", 0)
        cumulative["total_images_space_saved_bytes"] += run_stats.get("images_space_saved", 0)

        # Update format statistics (now stored as nested dict)
        run_format_stats = run_stats.get("format_stats", {})
        cumulative_format_stats = cumulative.get("format_stats", {})

        for format_ext, format_data in run_format_stats.items():
            if format_ext not in cumulative_format_stats:
                cumulative_format_stats[format_ext] = {
                    "count": 0,
                    "original_size": 0,
                    "compressed_size": 0,
                    "space_saved": 0,
                }
            cumulative_format_stats[format_ext]["count"] += format_data.get("count", 0)
            cumulative_format_stats[format_ext]["original_size"] += format_data.get("original_size", 0)
            cumulative_format_stats[format_ext]["compressed_size"] += format_data.get("compressed_size", 0)
            cumulative_format_stats[format_ext]["space_saved"] += format_data.get("space_saved", 0)

        cumulative["format_stats"] = cumulative_format_stats
        cumulative["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.save_cumulative_stats(cumulative)

    def save_cumulative_stats(self, stats: Dict) -> None:
        """
        Save cumulative statistics to JSON file.

        Args:
            stats: Dictionary with cumulative statistics
        """
        try:
            with open(self.cumulative_stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.cumulative_stats_file}")
        except Exception as e:
            print(f"Warning: Error saving cumulative statistics ({e})")

    def append_run_history(self, run_stats: Dict, cmd_args: Dict, run_uuid: str) -> None:
        """
        Append current run to run history JSON file.

        Args:
            run_stats: Statistics dictionary from current compression run
            cmd_args: Command line arguments used for this run
            run_uuid: Unique identifier for this compression run
        """
        try:
            # Load existing history
            history = self.load_run_history()

            # Prepare run record
            run_record = {
                "run_id": run_uuid,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_folder": cmd_args.get("source_folder", "N/A"),
                "files_processed": run_stats.get("processed", 0),
                "files_skipped": run_stats.get("skipped", 0),
                "files_errors": run_stats.get("errors", 0),
                "space_saved_bytes": run_stats.get("space_saved", 0),
                "videos_processed": run_stats.get("videos_processed", 0),
                "images_processed": run_stats.get("images_processed", 0),
                "videos_original_size_bytes": run_stats.get("videos_original_size", 0),
                "videos_compressed_size_bytes": run_stats.get("videos_compressed_size", 0),
                "videos_space_saved_bytes": run_stats.get("videos_space_saved", 0),
                "images_original_size_bytes": run_stats.get("images_original_size", 0),
                "images_compressed_size_bytes": run_stats.get("images_compressed_size", 0),
                "images_space_saved_bytes": run_stats.get("images_space_saved", 0),
                "format_stats": run_stats.get("format_stats", {}),
                "processing_time_seconds": run_stats.get("total_processing_time", 0.0),
                "video_crf": cmd_args.get("video_crf"),
                "image_quality": cmd_args.get("image_quality"),
                "recursive": cmd_args.get("recursive", False),
                "overwrite": cmd_args.get("overwrite", False),
            }

            # Append new record
            history.append(run_record)

            # Save updated history
            with open(self.run_history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.run_history_file}")
        except Exception as e:
            print(f"Warning: Error saving run history ({e})")

    def print_stats(self) -> None:
        """Print cumulative statistics in a nice format."""
        stats = self.load_cumulative_stats()

        if stats["total_runs"] == 0:
            print("\n" + "=" * 60)
            print("No Statistics Available")
            print("=" * 60)
            print("Statistics will be created after your first compression run.")
            return

        print("\n" + "=" * 60)
        print("Cumulative Compression Statistics")
        print("=" * 60)
        print(f"Total Runs: {stats['total_runs']}")
        print(f"Last Updated: {stats['last_updated'] or 'N/A'}")
        print()
        print("File Statistics:")
        print(f"  Processed: {stats['total_files_processed']:,} files")
        print(f"  Skipped: {stats['total_files_skipped']:,} files")
        print(f"  Errors: {stats['total_files_errors']:,} files")

        # Type-level breakdown (only show if > 0)
        videos_processed = stats.get("total_videos_processed", 0)
        images_processed = stats.get("total_images_processed", 0)
        videos_skipped = stats.get("total_videos_skipped", 0)
        images_skipped = stats.get("total_images_skipped", 0)
        videos_errors = stats.get("total_videos_errors", 0)
        images_errors = stats.get("total_images_errors", 0)

        if videos_processed > 0 or images_processed > 0:
            print()
            print("By Type:")
            if videos_processed > 0 or videos_skipped > 0 or videos_errors > 0:
                print(f"  Videos: {videos_processed:,} processed, {videos_skipped:,} skipped, {videos_errors:,} errors")
            if images_processed > 0 or images_skipped > 0 or images_errors > 0:
                print(f"  Images: {images_processed:,} processed, {images_skipped:,} skipped, {images_errors:,} errors")

        print()
        print("Size Statistics:")
        original_size = stats["total_original_size_bytes"]
        compressed_size = stats["total_compressed_size_bytes"]
        space_saved = stats["total_space_saved_bytes"]

        print(f"  Original Size: {format_size(original_size)}")
        print(f"  Compressed Size: {format_size(compressed_size)}")
        print(f"  Space Saved: {format_size(space_saved)}")

        if original_size > 0:
            compression_ratio = (space_saved / original_size) * 100
            print(f"  Overall Compression: {compression_ratio:.2f}%")

        # Type-level size breakdown (only show if > 0)
        videos_original = stats.get("total_videos_original_size_bytes", 0)
        videos_compressed = stats.get("total_videos_compressed_size_bytes", 0)
        videos_space_saved = stats.get("total_videos_space_saved_bytes", 0)
        images_original = stats.get("total_images_original_size_bytes", 0)
        images_compressed = stats.get("total_images_compressed_size_bytes", 0)
        images_space_saved = stats.get("total_images_space_saved_bytes", 0)

        if videos_original > 0 or images_original > 0:
            print()
            print("Size by Type:")
            if videos_original > 0:
                print(
                    f"  Videos: {format_size(videos_original)} → {format_size(videos_compressed)} "
                    f"({format_size(videos_space_saved)} saved)"
                )
                if videos_original > 0:
                    video_ratio = (videos_space_saved / videos_original) * 100
                    print(f"    Compression: {video_ratio:.2f}%")
            if images_original > 0:
                print(
                    f"  Images: {format_size(images_original)} → {format_size(images_compressed)} "
                    f"({format_size(images_space_saved)} saved)"
                )
                if images_original > 0:
                    image_ratio = (images_space_saved / images_original) * 100
                    print(f"    Compression: {image_ratio:.2f}%")

        # Format-level breakdown (only show formats with count > 0)
        format_stats = stats.get("format_stats", {})
        if format_stats:
            # Sort formats by count (descending)
            sorted_formats = sorted(format_stats.items(), key=lambda x: x[1].get("count", 0), reverse=True)
            # Only show formats with count > 0
            formats_to_show = [(ext, data) for ext, data in sorted_formats if data.get("count", 0) > 0]

            if formats_to_show:
                print()
                print("By Format:")
                for format_ext, format_data in formats_to_show:
                    count = format_data.get("count", 0)
                    orig_size = format_data.get("original_size", 0)
                    comp_size = format_data.get("compressed_size", 0)
                    saved = format_data.get("space_saved", 0)
                    print(
                        f"  .{format_ext.upper()}: {count:,} files, "
                        f"{format_size(orig_size)} → {format_size(comp_size)} "
                        f"({format_size(saved)} saved)"
                    )
                    if orig_size > 0:
                        format_ratio = (saved / orig_size) * 100
                        print(f"    Compression: {format_ratio:.2f}%")

        print("=" * 60)

    def load_run_history(self) -> List[Dict]:
        """
        Load run history from JSON file.

        Returns:
            List of dictionaries containing run history records
        """
        if not self.run_history_file.exists():
            return []

        try:
            with open(self.run_history_file, "r", encoding="utf-8") as f:
                runs = json.load(f)
            return runs if isinstance(runs, list) else []
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Error reading run history ({e})")
            return []
        except Exception as e:
            print(f"Warning: Error reading run history ({e})")
            return []

    def print_history(self, limit: Optional[int] = None) -> None:
        """
        Print run history in a nice format.

        Args:
            limit: Maximum number of runs to display (None for all)
        """
        runs = self.load_run_history()

        if not runs:
            print("\n" + "=" * 60)
            print("No Run History Available")
            print("=" * 60)
            print("Run history will be created after your first compression run.")
            return

        # Reverse to show most recent first
        runs.reverse()

        if limit:
            runs = runs[:limit]

        print("\n" + "=" * 60)
        print(f"Run History ({len(runs)} of {len(self.load_run_history())} runs shown)")
        print("=" * 60)

        for idx, run in enumerate(runs, 1):
            print(f"\nRun #{idx}")
            if "run_id" in run:
                print(f"  Run ID: {run['run_id']}")
            print(f"  Timestamp: {run.get('timestamp', 'N/A')}")
            print(f"  Source Folder: {run.get('source_folder', 'N/A')}")
            print(
                f"  Files: {run.get('files_processed', 0)} processed, "
                f"{run.get('files_skipped', 0)} skipped, "
                f"{run.get('files_errors', 0)} errors"
            )

            space_saved = run.get("space_saved_bytes", 0)
            print(f"  Space Saved: {format_size(space_saved)}")

            time_seconds = run.get("processing_time_seconds", 0)
            if time_seconds > 0:
                hours = int(time_seconds // 3600)
                minutes = int((time_seconds % 3600) // 60)
                seconds = time_seconds % 60
                if hours > 0:
                    time_str = f"{hours}h {minutes}m {seconds:.1f}s"
                elif minutes > 0:
                    time_str = f"{minutes}m {seconds:.1f}s"
                else:
                    time_str = f"{seconds:.1f}s"
                print(f"  Processing Time: {time_str}")

            print(
                f"  Settings: CRF={run.get('video_crf', 'N/A')}, "
                f"Quality={run.get('image_quality', 'N/A')}, "
                f"Recursive={run.get('recursive', False)}, "
                f"Overwrite={run.get('overwrite', False)}"
            )

        print("\n" + "=" * 60)

    def load_files_log(self) -> List[Dict]:
        """
        Load complete file processing history from files.json.

        Returns:
            List of dictionaries containing file processing records
        """
        if not self.files_log_file.exists():
            return []

        try:
            with open(self.files_log_file, "r", encoding="utf-8") as f:
                files = json.load(f)
            return files if isinstance(files, list) else []
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Error reading files log ({e})")
            return []
        except Exception as e:
            print(f"Warning: Error reading files log ({e})")
            return []

    def append_to_files_log(self, files_data: List[Dict], run_uuid: str, cmd_args: Dict) -> None:
        """
        Append files from current run to files.json.

        Args:
            files_data: List of file info dictionaries from current run
            run_uuid: Unique identifier for this compression run
            cmd_args: Command line arguments used for this run
        """
        try:
            # Load existing files log
            files_log = self.load_files_log()

            # Process each file and add to log
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for file_info in files_data:
                # Extract file type and format from name
                file_name = file_info.get("name", "")
                file_extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
                
                # Determine file type based on extension
                video_extensions = ["mp4", "avi", "mov", "mkv", "flv", "wmv", "webm", "m4v"]
                image_extensions = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg"]
                
                if file_extension in video_extensions:
                    file_type = "video"
                elif file_extension in image_extensions:
                    file_type = "image"
                else:
                    file_type = "unknown"
                
                # Create file record
                file_record = {
                    "timestamp": timestamp,
                    "run_id": run_uuid,
                    "file_name": file_name,
                    "original_path": file_info.get("original_path", "N/A"),
                    "new_path": file_info.get("new_path", "N/A"),
                    "file_type": file_type,
                    "format": file_extension,
                    "modifications": {
                        "compressed": file_info.get("status") == "processed",
                        "video_crf": cmd_args.get("video_crf") if file_type == "video" else None,
                        "video_preset": cmd_args.get("video_preset") if file_type == "video" else None,
                        "video_resize": cmd_args.get("video_resize") if file_type == "video" else None,
                        "image_quality": cmd_args.get("image_quality") if file_type == "image" else None,
                        "image_resize": cmd_args.get("image_resize") if file_type == "image" else None,
                    },
                    "size_before_bytes": file_info.get("original_size", 0),
                    "size_after_bytes": file_info.get("compressed_size", 0),
                    "space_saved_bytes": file_info.get("space_saved", 0),
                    "compression_ratio_percent": file_info.get("compression_ratio", 0.0),
                    "processing_time_seconds": file_info.get("processing_time", 0.0),
                    "status": file_info.get("status", "unknown"),
                }
                
                files_log.append(file_record)

            # Save updated files log
            with open(self.files_log_file, "w", encoding="utf-8") as f:
                json.dump(files_log, f, indent=2)
        except PermissionError:
            print(f"Warning: Permission denied when writing to {self.files_log_file}")
        except Exception as e:
            print(f"Warning: Error saving files log ({e})")
