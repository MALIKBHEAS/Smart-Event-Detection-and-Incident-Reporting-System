import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app
from app.workers.worker import RTSPDetectionWorker
from app.workers.manager import WorkerConfig

@patch('app.workers.worker.av')
def test_audio_failure_does_not_break_auth(mock_av):
    # Simulate Connection Refused for audio
    mock_av.open.side_effect = Exception('[Errno 111] Connection refused: rtsp://admin:admin123@192.168.1.11/live')
    
    config = WorkerConfig(
        source='rtsp://admin:admin123@192.168.1.11/live',
        camera_id=999,
        camera_name='TestCam',
        detector_name='dummy',
        fps=5.0,
        confidence_threshold=0.5,
        frame_skip=0,
        event_detectors=[]
    )
    
    with patch('app.workers.worker.cv2.VideoCapture') as mock_cap,          patch('app.workers.worker.YAMNetDetector') as mock_yamnet,          patch('app.workers.worker.EventFusionService'):
        mock_cap.return_value.isOpened.return_value = True
        mock_cap.return_value.read.return_value = (True, None)
        mock_detector = MagicMock()
        mock_yamnet.return_value = mock_detector
        
        worker = RTSPDetectionWorker(config)
        worker._audio_detector = mock_detector
        
        # Start worker manually to isolate thread test
        worker._stop_requested = False
        worker._reader_stop = threading.Event()
        
        audio_thread = threading.Thread(target=worker._audio_reader_loop)
        audio_thread.start()
        
        # Wait a moment for audio thread to hit exception and log it
        time.sleep(0.5)
        
        with TestClient(app) as test_client:
            # 1. Unauthenticated API should still be up (FastAPI not blocked)
            res = test_client.get('/health')
            assert res.status_code == 200
            
            # 2. Authenticated API should return normal 401 Unauthenticated, NOT crash
            res = test_client.get('/api/auth/me')
            assert res.status_code in [401, 404]
        
        # 3. Video thread / worker is NOT stopped
        assert worker._stop_requested is False
        assert worker._reader_stop.is_set() is False
        
        # Cleanup
        worker._reader_stop.set()
        worker._stop_requested = True
        audio_thread.join(timeout=2.0)
