from app.workers.worker import RTSPDetectionWorker, WorkerConfig


def test_rtsp_detection_worker_initializes_detector():
    config = WorkerConfig(source=0, camera_id=1, camera_name="test-camera", fps=1.0)
    worker = RTSPDetectionWorker(config)
    assert worker._detector is not None
    assert worker.camera_name == "test-camera"
    assert worker.camera_id == 1
