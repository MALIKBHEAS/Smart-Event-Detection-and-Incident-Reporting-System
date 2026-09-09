import cv2
from ultralytics import YOLO

def main():
    print("جاري تحميل نموذج YOLO...")
    model = YOLO("yolov8n.pt")
    
    print("جاري فتح الكاميرا...")
    # فتح الكاميرا باستخدام مكتبة OpenCV الأساسية
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("خطأ: لم نتمكن من الوصول إلى الكاميرا.")
        return

    print("تم فتح الكاميرا بنجاح! النافذة ستظهر الآن.")
    print("اضغط على حرف 'q' داخل النافذة لإغلاقها.")

    while True:
        success, frame = cap.read()
        if not success:
            print("لم يتمكن من قراءة الصورة من الكاميرا.")
            break
            
        # تشغيل التتبع على الصورة الحالية
        # persist=True ضروري جداً لكي يتذكر الكود مسار الأجسام السابقة
        results = model.track(frame, persist=True, verbose=False)
        
        # رسم المربعات (Bounding Boxes) على الصورة
        annotated_frame = results[0].plot()
        
        # عرض النافذة بشكل مباشر ومضمون
        cv2.imshow("YOLO Object Tracking", annotated_frame)
        
        # انتظار 1 ملي ثانية للإطار، وإذا تم الضغط على q نخرج
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
            
    # إغلاق الكاميرا والنوافذ بعد الانتهاء
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
