from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.domain.detection import DetectionResult, RawDetection
from app.workers.pipeline.context import ProcessedFrame
from app.workers.pipeline.frame_processor import DetectionFrameProcessor
from app.workers.worker import RTSPDetectionWorker, WorkerConfig


class StubDetector:
    def detect(self, frame: object, conf: float = 0.5) -> list[RawDetection]:
        return [
            RawDetection(
                id="1",
                class_id=0,
                class_name="person",
                label="person",
                confidence=0.9,
                bbox=(10.0, 10.0, 20.0, 20.0),
                timestamp=1.0,
            )
        ]


@pytest.mark.asyncio
async def test_worker_uses_frame_processor(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.workers.worker.default_detector",
        lambda **kwargs: StubDetector(),
    )

    worker = RTSPDetectionWorker(
        WorkerConfig(source="dummy", camera_id=1, camera_name="integration-cam", fps=5.0)
    )
    assert worker._frame_processor is not None
    assert isinstance(worker._frame_processor, DetectionFrameProcessor)


@pytest.mark.asyncio
async def test_worker_handle_processed_frame_ingests_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "app.workers.worker.default_detector",
        lambda **kwargs: StubDetector(),
    )

    worker = RTSPDetectionWorker(
        WorkerConfig(source="dummy", camera_id=7, camera_name="ingest-cam", fps=5.0)
    )
    worker.evidence_root = tmp_path

    ingest_mock = MagicMock(return_value=42)
    monkeypatch.setattr(worker._fusion_service, "ingest", ingest_mock)

    processed = ProcessedFrame(
        timestamp=10.0,
        frame=MagicMock(),
        events=[
            DetectionResult(
                detector="detection",
                detection_id="1",
                track_id="1",
                label="person",
                score=0.9,
                metadata={"bbox": (1, 2, 3, 4)},
            )
        ],
    )

    await worker._handle_processed_frame(processed)
    ingest_mock.assert_called_once()


@pytest.mark.asyncio
async def test_worker_processing_loop_delegates_to_pipeline(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.workers.worker.default_detector",
        lambda **kwargs: StubDetector(),
    )

    worker = RTSPDetectionWorker(
        WorkerConfig(source="dummy", camera_id=3, camera_name="loop-cam", fps=5.0)
    )

    processed = ProcessedFrame(
        timestamp=1.0,
        frame=object(),
        filtered_detections=[
            RawDetection(
                id="1",
                class_id=0,
                class_name="person",
                label="person",
                confidence=0.9,
                bbox=(1.0, 1.0, 2.0, 2.0),
                timestamp=1.0,
            )
        ],
        events=[],
    )

    handle_mock = AsyncMock()
    monkeypatch.setattr(worker, "_handle_processed_frame", handle_mock)
    monkeypatch.setattr(worker._frame_processor, "process", lambda context: processed)

    worker._stop_requested = False
    worker._frame_queue = asyncio.Queue()
    await worker._frame_queue.put((1.0, object()))

    async def stop_after_one() -> None:
        await asyncio.sleep(0.05)
        worker._stop_requested = True

    asyncio.create_task(stop_after_one())
    await worker._processing_loop()

    handle_mock.assert_awaited_once()


def test_worker_detector_name_uses_registry(monkeypatch) -> None:
    created = {}

    class NamedDetector(StubDetector):
        pass

    def fake_get_detector(name: str, **kwargs):
        created["name"] = name
        return NamedDetector()

    monkeypatch.setattr("app.workers.worker.get_detector", fake_get_detector)

    worker = RTSPDetectionWorker(
        WorkerConfig(
            source="dummy",
            camera_id=4,
            camera_name="registry-cam",
            detector_name="noop",
        )
    )
    assert created["name"] == "noop"
    assert worker._detector is not None
