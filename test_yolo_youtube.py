import os
import requests
from ultralytics import YOLO

def download_sample_video(filename):
    url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/car-detection.mp4"
    if not os.path.exists(filename):
        print("جاري تحميل فيديو اختباري صغير للسيارات...")
        response = requests.get(url, stream=True)
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print("تم التحميل بنجاح!")
    else:
        print("الفيديو الاختباري موجود بالفعل.")

def main():
    model = YOLO("yolov8n.pt")
    
    video_path = "sample_video.mp4"
    
    # تحميل فيديو محلي للتجربة وتخطي حظر اليوتيوب
    download_sample_video(video_path)
    
    print(f"جاري بدء التتبع على الفيديو: {video_path}")
    
    try:
        # تشغيل التتبع (Tracking)
        results = model.track(source=video_path, show=True, tracker="bytetrack.yaml", stream=True)
        
        for result in results:
            pass
    except Exception as e:
        print(f"حدث خطأ أثناء التتبع: {e}")

if __name__ == "__main__":
    main()
