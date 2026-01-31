"""Tests for progress tracking."""

import random
from types import SimpleNamespace

from byteit.progress import ProgressTracker


class FakeBar:
    """Simple progress bar stub for tests."""

    def __init__(self, *args, **kwargs):
        self.description = None
        self.total_updates = 0.0
        self.closed = False

    def set_description(self, desc: str) -> None:
        self.description = desc

    def update(self, n: float) -> None:
        self.total_updates += n

    def close(self) -> None:
        self.closed = True


def test_progress_message_ranges():
    tracker = ProgressTracker(progress_bar_factory=FakeBar)

    assert tracker._progress_message(0) == "Upload"
    assert tracker._progress_message(10) == "Preprocessing"
    assert tracker._progress_message(24.9) == "Preprocessing"
    assert tracker._progress_message(25) == "Parsing"
    assert tracker._progress_message(69.9) == "Parsing"
    assert tracker._progress_message(70) == "Post-processing"
    assert tracker._progress_message(89.9) == "Post-processing"
    assert tracker._progress_message(90) == "Validation"


def test_estimate_times_for_extensions(monkeypatch):
    tracker = ProgressTracker(progress_bar_factory=FakeBar)

    monkeypatch.setattr(random, "gauss", lambda mean, sigma: mean)
    monkeypatch.setattr(random, "uniform", lambda a, b: (a + b) / 2)

    assert tracker._estimate_processing_seconds("docx", None) == 6.0
    assert tracker._estimate_processing_seconds("pptx", None) == 6.0
    assert tracker._estimate_processing_seconds("pdf", 2) == 22.5
    assert tracker._estimate_processing_seconds("txt", None) == 3.0


def test_update_advances_progress_with_time():
    time_values = [0.0]

    def fake_time():
        return time_values[0]

    tracker = ProgressTracker(progress_bar_factory=FakeBar, time_provider=fake_time)
    tracker._state.estimated_seconds = 10.0

    job = SimpleNamespace(metadata=None)

    time_values[0] = 2.5
    tracker.update(job)

    assert tracker._bar.description == "Preprocessing"  # 22.5%
    assert tracker._bar.total_updates == 22.5

    time_values[0] = 5.0
    tracker.update(job)

    assert tracker._bar.description == "Parsing"  # 45%
    assert tracker._bar.total_updates == 45.0


def test_finalize_completes_bar():
    tracker = ProgressTracker(progress_bar_factory=FakeBar)
    tracker._state.last_progress = 90.0

    tracker.finalize()

    assert tracker._bar.total_updates == 10.0
    assert tracker._bar.description == "Validation"
    assert tracker._bar.closed is True


def test_page_count_updates_pdf_estimate():
    """Test that PDF page count dynamically updates estimate."""
    tracker = ProgressTracker(progress_bar_factory=FakeBar)
    tracker._input_extension = "pdf"
    tracker._state.estimated_seconds = 10.0

    job_with_pages = SimpleNamespace(
        metadata=SimpleNamespace(page_count=5)
    )
    
    tracker.update(job_with_pages)
    
    assert tracker._state.known_pages == 5
    assert tracker._state.estimated_seconds > 10.0  # Should be recalculated


def test_progress_does_not_exceed_90_during_processing():
    """Test that progress caps at 90% during processing phase."""
    time_values = [0.0]

    def fake_time():
        return time_values[0]

    tracker = ProgressTracker(progress_bar_factory=FakeBar, time_provider=fake_time)
    tracker._state.estimated_seconds = 10.0

    job = SimpleNamespace(metadata=None)

    # Simulate time far beyond estimated completion
    time_values[0] = 100.0
    tracker.update(job)

    # Should not exceed 90%
    assert tracker._bar.total_updates == 90.0
    assert tracker._bar.description == "Validation"


def test_close_without_finalize():
    """Test that close() can be called without finalize()."""
    tracker = ProgressTracker(progress_bar_factory=FakeBar)
    tracker._state.last_progress = 50.0

    tracker.close()

    assert tracker._bar.closed is True
    # Should not have completed to 100
    assert tracker._bar.total_updates < 100
