"""Progress tracking for ByteIT document processing."""

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from tqdm import tqdm

from .connectors import InputConnector, LocalFileInputConnector


class ProgressBar(Protocol):
    """Protocol for progress bar implementations."""

    def set_description(self, desc: str) -> None:
        ...

    def update(self, n: float) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass
class ProgressState:
    """Internal progress state."""

    estimated_seconds: float
    start_time: float
    last_progress: float
    known_pages: Optional[int]


class ProgressTracker:
    """Track and display progress while processing a document."""

    def __init__(
        self,
        input_connector: Optional[InputConnector] = None,
        progress_bar_factory=tqdm,
        time_provider=time.time,
    ) -> None:
        self._input_extension = self._get_input_extension(input_connector)
        self._time_provider = time_provider
        self._bar: ProgressBar = progress_bar_factory(
            total=100,
            unit="%",
            bar_format="{l_bar}{bar}| {n:.2f}/{total:.2f}",
            colour="#6b75fe",
        )
        # PDF: baseline 85s + 6-8s por página
        baseline = 0.0
        if self._input_extension == "pdf":
            baseline = 85.0
        self._state = ProgressState(
            estimated_seconds=max(
                baseline, self._estimate_processing_seconds(self._input_extension, None)
            ),
            start_time=self._time_provider(),
            last_progress=0.0,
            known_pages=None,
        )

    def update(self, job: object) -> None:
        """Update progress based on job status."""
        metadata = getattr(job, "metadata", None)
        page_count = getattr(metadata, "page_count", None) if metadata else None
        if page_count and isinstance(page_count, int) and page_count != self._state.known_pages:
            self._state.known_pages = page_count
            if self._input_extension == "pdf":
                # PDF: baseline 85s + 6-8s por página
                per_page = random.uniform(6.0, 8.0)
                self._state.estimated_seconds = 85.0 + per_page * page_count
            else:
                self._state.estimated_seconds = self._estimate_processing_seconds(
                    self._input_extension, page_count
                )

        elapsed = self._time_provider() - self._state.start_time
        if self._state.estimated_seconds > 0:
            target_progress = min(
                90.0, (elapsed / self._state.estimated_seconds) * 90.0
            )
        else:
            target_progress = 90.0

        if target_progress > self._state.last_progress:
            self._bar.set_description(self._progress_message(target_progress))
            self._bar.update(target_progress - self._state.last_progress)
            self._state.last_progress = target_progress

    def finalize(self) -> None:
        """Finalize progress at completion. If finished too fast (PDF), smooth bar to 100%."""
        # If PDF and finished much faster than baseline, smooth the last part
        if self._input_extension == "pdf":
            elapsed = self._time_provider() - self._state.start_time
            # If finished >10s faster than baseline, animate last part
            if elapsed < self._state.estimated_seconds - 10:
                remaining = 100 - self._state.last_progress
                if remaining > 0:
                    steps = 40
                    step = remaining / steps
                    for i in range(steps):
                        self._bar.set_description("Download")
                        self._bar.update(step)
                        self._state.last_progress += step
                        time.sleep(2.0 / steps)
                    self._state.last_progress = 100.0
                    self._bar.set_description("Download")
                    self._bar.n = 100
                    self._bar.refresh()
                    self._bar.close()
                    return
        if self._state.last_progress < 100:
            self._bar.set_description("Download")
            self._bar.update(100 - self._state.last_progress)
            self._state.last_progress = 100.0
        self._bar.close()

    def close(self) -> None:
        """Close progress bar without finalizing."""
        self._bar.close()

    def _get_input_extension(self, input_connector: Optional[InputConnector]) -> str:
        """Get lowercase file extension from input connector if available."""
        if input_connector is None:
            return ""

        if isinstance(input_connector, LocalFileInputConnector):
            return input_connector.file_path.suffix.lower().lstrip(".")

        filename = getattr(input_connector, "filename", "")
        if filename:
            return Path(filename).suffix.lower().lstrip(".")

        return ""

    def _estimate_processing_seconds(
        self, file_extension: str, page_count: Optional[int]
    ) -> float:
        """Estimate processing time for progress simulation."""
        extension = (file_extension or "").lower()

        if extension in ("docx", "pptx"):
            return max(2.0, min(10.0, random.gauss(6.0, 2.0)))

        if extension == "pdf":
            pages = page_count if page_count and page_count > 0 else 1
            per_page = random.uniform(7.5, 15.0)
            return pages * per_page

        return max(1.0, min(5.0, random.gauss(3.0, 1.0)))

    def _progress_message(self, progress: float) -> str:
        """Select grounded progress messages by phase."""
        if progress < 10:
            return "Upload"
        if progress < 25:
            return "Preprocessing"
        if progress < 70:
            return "Parsing"
        if progress < 90:
            return "Post-processing"
        return "Download"
