import asyncio
import time
from unittest.mock import MagicMock, patch

from app.workers.worker import RTSPDetectionWorker, WorkerConfig


def test_worker_reconnect_releases_capture():
    config = WorkerConfig(
        camera_id=1,
        camera_name="TestCamera",
        source="rtsp://fake",
        fps=10.0,
        detector_name="yolov8n",
        device="cpu",
    )
    
    mock_cap = MagicMock()
    mock_cap.read.return_value = (False, None)
    mock_cap.isOpened.return_value = True

    worker = RTSPDetectionWorker(config)
    
    with patch("app.workers.worker.cv2.VideoCapture", return_value=mock_cap):
        worker._cap = worker._open_capture()
        assert worker._cap is not None
        
        import threading
        
        worker._loop = asyncio.new_event_loop()
        worker._frame_queue = asyncio.Queue(maxsize=1)
        
        t = threading.Thread(target=worker._reader_loop)
        t.daemon = True
        t.start()
        
        time.sleep(1.0)
        
        assert worker._cap is None, "VideoCapture was not set to None after read failure"
        mock_cap.release.assert_called()
        
        worker._stop_requested = True
        t.join(timeout=1.0)
