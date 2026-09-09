import csv
import logging
import time
from typing import List

import numpy as np

try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    try:
        import tensorflow.lite as tflite
    except ImportError:
        tflite = None

logger = logging.getLogger(__name__)

class YAMNetDetector:
    def __init__(self, model_path: str = "yamnet.tflite", class_map_path: str = "yamnet_class_map.csv"):
        self.model_path = model_path
        self.interpreter = None
        self.class_names = []
        
        if tflite is None:
            logger.warning("tflite_runtime not installed. Audio detection will be disabled.")
            return

        try:
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            self.class_names = self._load_class_map(class_map_path)
        except Exception as exc:
            logger.error("Failed to initialize YAMNet: %s", exc)
            self.interpreter = None
        
        # Audio Events we actually care about in the SOC
        self.target_classes = {
            "Gunshot, gunfire",
            "Explosion",
            "Glass",
            "Shatter",
            "Scream",
            "Shout",
            "Siren",
            "Alarm clock",
            "Fire alarm",
            "Civil defense siren",
            "Police car (siren)",
            "Ambulance (siren)",
            "Fire engine, fire truck (siren)",
            "Car alarm",
            "Emergency vehicle"
        }
        
    def _load_class_map(self, path: str) -> List[str]:
        classes = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for row in reader:
                    classes.append(row[2])
        except Exception as e:
            logger.error("Failed to load yamnet class map: %s", e)
        return classes

    def detect(self, waveform: np.ndarray) -> List[dict]:
        """
        waveform: 1D numpy array of floats in range [-1.0, 1.0], 16kHz
        Expected shape for YAMNet: (N,) where N is typically 15600 (0.975s)
        """
        if self.interpreter is None or len(waveform) == 0:
            return []
            
        # Ensure it's float32
        waveform = np.array(waveform, dtype=np.float32)
        
        # set input tensor
        self.interpreter.set_tensor(self.input_details[0]['index'], waveform)
        self.interpreter.invoke()
        
        # get output
        scores = self.interpreter.get_tensor(self.output_details[0]['index'])
        # YAMNet returns scores per 0.48s frame. We mean across frames.
        mean_scores = np.mean(scores, axis=0)
        
        top_indices = np.argsort(mean_scores)[::-1][:3]
        
        results = []
        now_ts = time.time()
        for idx in top_indices:
            score = float(mean_scores[idx])
            if score > 0.2:  # base threshold
                class_name = self.class_names[idx]
                if class_name in self.target_classes:
                    results.append({
                        "class_id": int(idx),
                        "class_name": class_name,
                        "label": class_name.lower(),
                        "confidence": score,
                        "timestamp": now_ts
                    })
        return results
