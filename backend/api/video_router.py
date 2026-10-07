from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import numpy as np
import base64
import json
import os
import joblib
import tensorflow as tf
from collections import deque
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CORE_DIR = os.path.join(BASE_DIR, "core")

model_asset_path = os.path.join(CORE_DIR, "pose_landmarker_full.task")

if not os.path.exists(model_asset_path):
    print(f"⚠️ 에러: {model_asset_path} 파일이 존재하지 않습니다. 모델 파일을 먼저 다운로드하세요.")

base_options = python.BaseOptions(model_asset_path=model_asset_path)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.IMAGE,
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.PoseLandmarker.create_from_options(options)

try:
    model = tf.keras.models.load_model(os.path.join(CORE_DIR, "kinetic_lstm_model.keras"))
    scaler = joblib.load(os.path.join(CORE_DIR, "scaler.pkl"))
    encoder = joblib.load(os.path.join(CORE_DIR, "encoder.pkl"))
    print("✅ AI 모델, 스케일러, 인코더 로드 성공!")
except Exception as e:
    print(f"⚠️ 모델/스케일러/인코더 로드 실패: {e}")

SEQ_LENGTH = 60

@router.websocket("/ws/video")
async def websocket_video_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ 핸드폰 앱과 실시간 연결 성공!")
    
    frame_sequence = deque(maxlen=SEQ_LENGTH)
    
    try:
        while True:
            data = await websocket.receive_text()
            img_data = base64.b64decode(data)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                continue

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        
            detection_result = detector.detect(mp_image)

            if detection_result.pose_landmarks and len(detection_result.pose_landmarks) > 0:
                landmarks = detection_result.pose_landmarks[0] 
                
                def get_pt(idx): 
                    return [landmarks[idx].x, landmarks[idx].y]
                
                center_shoulder = [
                    (landmarks[11].x + landmarks[12].x) / 2, 
                    (landmarks[11].y + landmarks[12].y) / 2
                ]
                center_hip = [
                    (landmarks[23].x + landmarks[24].x) / 2, 
                    (landmarks[23].y + landmarks[24].y) / 2
                ]

                neck = center_shoulder
                back = [
                    center_shoulder[0] + (center_hip[0] - center_shoulder[0]) * (1/3),
                    center_shoulder[1] + (center_hip[1] - center_shoulder[1]) * (1/3)
                ]
                waist = [
                    center_shoulder[0] + (center_hip[0] - center_shoulder[0]) * (2/3),
                    center_shoulder[1] + (center_hip[1] - center_shoulder[1]) * (2/3)
                ]

                l_palm = [(landmarks[15].x + landmarks[19].x) / 2, (landmarks[15].y + landmarks[19].y) / 2]
                r_palm = [(landmarks[16].x + landmarks[20].x) / 2, (landmarks[16].y + landmarks[20].y) / 2]
                l_foot = [(landmarks[27].x + landmarks[31].x) / 2, (landmarks[27].y + landmarks[31].y) / 2]
                r_foot = [(landmarks[28].x + landmarks[32].x) / 2, (landmarks[28].y + landmarks[32].y) / 2]

                keypoints = []
                keypoints.extend(get_pt(0))   # 1. Nose
                keypoints.extend(get_pt(2))   # 2. Left Eye
                keypoints.extend(get_pt(5))   # 3. Right Eye
                keypoints.extend(get_pt(7))   # 4. Left Ear
                keypoints.extend(get_pt(8))   # 5. Right Ear
                keypoints.extend(get_pt(11))  # 6. Left Shoulder
                keypoints.extend(get_pt(12))  # 7. Right Shoulder
                keypoints.extend(get_pt(13))  # 8. Left Elbow
                keypoints.extend(get_pt(14))  # 9. Right Elbow
                keypoints.extend(get_pt(15))  # 10. Left Wrist
                keypoints.extend(get_pt(16))  # 11. Right Wrist
                keypoints.extend(get_pt(23))  # 12. Left Hip
                keypoints.extend(get_pt(24))  # 13. Right Hip
                keypoints.extend(get_pt(25))  # 14. Left Knee
                keypoints.extend(get_pt(26))  # 15. Right Knee
                keypoints.extend(get_pt(27))  # 16. Left Ankle
                keypoints.extend(get_pt(28))  # 17. Right Ankle
                
                keypoints.extend(neck)        # 18. Neck
                keypoints.extend(l_palm)      # 19. Left Palm
                keypoints.extend(r_palm)      # 20. Right Palm
                keypoints.extend(back)        # 21. Back
                keypoints.extend(waist)       # 22. Waist
                keypoints.extend(l_foot)      # 23. Left Foot 
                keypoints.extend(r_foot)      # 24. Right Foot

                frame_sequence.append(keypoints)

                if len(frame_sequence) == SEQ_LENGTH:
                    input_data = np.array(frame_sequence)
                    input_scaled = scaler.transform(input_data)
                    input_final = np.expand_dims(input_scaled, axis=0)
                    
                    prediction = model.predict(input_final, verbose=0)
                    class_idx = np.argmax(prediction)
                    max_prob = float(np.max(prediction))
                    
                    if max_prob >= 0.80:
                        predicted_label = encoder.inverse_transform([class_idx])[0]
                        try:
                            exercise_name, condition = predicted_label.split('_', 1)
                        except ValueError:
                            exercise_name = predicted_label
                            condition = "알 수 없음"

                        if condition == '정답':
                            border_color = "blue"
                            feedback_msg = "좋은 자세입니다!"
                        else:
                            border_color = "red"
                            feedback_msg = f"{condition} 자세를 교정해 주세요."

                        await websocket.send_text(json.dumps({
                            "status": "success", 
                            "color": border_color,
                            "feedback": feedback_msg,
                            "confidence": f"{max_prob*100:.1f}%"
                        }))
                    
                    for _ in range(20):
                        frame_sequence.popleft()
            
    except WebSocketDisconnect:
        print("❌ 핸드폰 앱과의 연결 종료")
    except Exception as e:
        print(f"❌ 서버 에러: {e}")