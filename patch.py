with open('backend/app/workers/pipeline/frame_processor.py') as f:
    c = f.read()

c = c.replace(
    'detector_objects = self._run_detector(frame_context)',
    'import time\n        t0 = time.time()\n        detector_objects = self._run_detector(frame_context)\n        yolo_lat = time.time() - t0\n        HealthRegistry.record_heartbeat("yolo", fps=round(1.0/yolo_lat,1) if yolo_lat>0 else 0)\n'
)

c = c.replace(
    'tracks, tracked_objects_out = self._update_tracks(\n            detector_objects, frame_context\n        )',
    't1 = time.time()\n        tracks, tracked_objects_out = self._update_tracks(\n            detector_objects, frame_context\n        )\n        HealthRegistry.record_heartbeat("tracker", latency_ms=round((time.time()-t1)*1000, 1))\n'
)

with open('backend/app/workers/pipeline/frame_processor.py', 'w') as f:
    f.write(c)

with open('backend/app/main.py') as f:
    mc = f.read()

if 'health_components_router' not in mc:
    mc = mc.replace(
        'app.include_router(settings_router)',
        'app.include_router(settings_router)\napp.include_router(health_components_router)'
    )
    mc = mc.replace(
        'from app.routers.settings import router as settings_router',
        'from app.routers.settings import router as settings_router\nfrom app.routers.health_components_router import router as health_components_router'
    )
    with open('backend/app/main.py', 'w') as f:
        f.write(mc)
