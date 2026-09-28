from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import numpy as np
import base64
import json
import mediapipe as mp
from collections import deque
import tensorflow as tf
import os
import joblib

router = APIRouter()

# 1. MediaPipe 포즈 추출기 초기화
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5
)

# 2. 모델, 스케일러, 인코더 로드 (model_trainer.py 실행 후 주석 해제)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CORE_DIR = os.path.join(BASE_DIR, "core")

try:
    model = tf.keras.models.load_model(os.path.join(CORE_DIR, "kinetic_lstm_model.h5"))
    scaler = joblib.load(os.path.join(CORE_DIR, "scaler.pkl"))
    encoder = joblib.load(os.path.join(CORE_DIR, "encoder.pkl"))
    print("✅ AI 모델, 스케일러, 인코더 로드 성공!")
except Exception as e:
    print(f"⚠️ 모델/스케일러/인코더 로드 실패: {e}")

# LSTM이 요구하는 시퀀스 길이
SEQ_LENGTH = 100

@router.websocket("/ws/video")
async def websocket_video_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ 핸드폰 앱과 실시간 연결 성공!")
    
    # 프레임 시퀀스를 저장할 버퍼 (최대 길이 100)
    frame_sequence = deque(maxlen=SEQ_LENGTH)
    
    try:
        while True:
            # 1. 클라이언트(모바일 앱)로부터 프레임 데이터 수신 (Base64 형식)
            data = await websocket.receive_text()
            
            # 2. Base64 문자열을 OpenCV 이미지로 디코딩
            img_data = base64.b64decode(data)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                continue

            # 3. MediaPipe에 이미지 전달을 위해 RGB 포맷으로 변환
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 4. 랜드마크 추출
            results = pose.process(image_rgb)

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                # Helper 함수: MediaPipe 랜드마크에서 x, y 좌표 추출
                def get_pt(idx): 
                    return [landmarks[idx].x, landmarks[idx].y]
                
                # --- AIHub 가이드라인 기반 특수 관절 계산 로직 ---
                
                # 양쪽 어깨와 골반의 중심점 (Neck, Back, Waist 계산을 위한 기준점)
                center_shoulder = [
                    (landmarks[11].x + landmarks[12].x) / 2, 
                    (landmarks[11].y + landmarks[12].y) / 2
                ]
                center_hip = [
                    (landmarks[23].x + landmarks[24].x) / 2, 
                    (landmarks[23].y + landmarks[24].y) / 2
                ]

                # 18. Neck (목): 원기둥의 중앙으로 간주, 양 어깨의 정중앙
                neck = center_shoulder
                
                # 21. Back (등): 어깨 중심과 골반 중심 사이 1/3 지점
                back = [
                    center_shoulder[0] + (center_hip[0] - center_shoulder[0]) * (1/3),
                    center_shoulder[1] + (center_hip[1] - center_shoulder[1]) * (1/3)
                ]
                
                # 22. Waist (허리): 어깨 중심과 골반 중심 사이 2/3 지점
                waist = [
                    center_shoulder[0] + (center_hip[0] - center_shoulder[0]) * (2/3),
                    center_shoulder[1] + (center_hip[1] - center_shoulder[1]) * (2/3)
                ]

                # 19, 20. Left/Right Palm: 손목(15/16)과 검지(19/20)의 중앙
                l_palm = [(landmarks[15].x + landmarks[19].x) / 2, (landmarks[15].y + landmarks[19].y) / 2]
                r_palm = [(landmarks[16].x + landmarks[20].x) / 2, (landmarks[16].y + landmarks[20].y) / 2]

                # 23, 24. Left/Right Foot: 발목(27/28)과 발끝(31/32)의 중앙 (Instep/발 중앙 대체)
                l_foot = [(landmarks[27].x + landmarks[31].x) / 2, (landmarks[27].y + landmarks[31].y) / 2]
                r_foot = [(landmarks[28].x + landmarks[32].x) / 2, (landmarks[28].y + landmarks[32].y) / 2]

                # ----------------------------------------------------

                # 5. 모델 입력 규격(24개 관절 순서)에 맞게 배열 조립
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
                
                # 계산된 특수 관절 추가
                keypoints.extend(neck)        # 18. Neck
                keypoints.extend(l_palm)      # 19. Left Palm
                keypoints.extend(r_palm)      # 20. Right Palm
                keypoints.extend(back)        # 21. Back
                keypoints.extend(waist)       # 22. Waist
                keypoints.extend(l_foot)      # 23. Left Foot 
                keypoints.extend(r_foot)      # 24. Right Foot

                # 완성된 48개의 특징점(Features)을 버퍼에 추가
                frame_sequence.append(keypoints)

                # 6. 100 프레임 시퀀스가 모이면 AI 분석 수행
                if len(frame_sequence) == SEQ_LENGTH:
                    input_data = np.array(frame_sequence)
                    
                    # 1) 스케일링 수행 (학습 시와 동일한 기준으로 0~1 사이로 정규화)
                    input_scaled = scaler.transform(input_data)
                    
                    # 2) 배치 차원 추가: (100, 48) -> (1, 100, 48)
                    input_final = np.expand_dims(input_scaled, axis=0)
                    
                    # 3) 모델 추론
                    prediction = model.predict(input_final, verbose=0)
                    
                    # 4) 가장 확률이 높은 클래스 인덱스 선택
                    class_idx = np.argmax(prediction)
                    
                    # 확률 임계값(Threshold) 추출
                    max_prob = float(np.max(prediction))
                    
                    # 인공지능이 80% 이상 확신할 때만 피드백을 전송하도록 제어
                    if max_prob >= 0.80:
                        predicted_label = encoder.inverse_transform([class_idx])[0]
                        await websocket.send_text(json.dumps({
                            "status": "success", 
                            "feedback": f"AI 분석 결과: {predicted_label} (확신도: {max_prob*100:.1f}%)"
                        }))
                    
                    # 제한적 오버래핑(Sliding Window) 도입
                    # 전체 60장 중 가장 오래된 20장(약 0.6초 분량)만 버리고 40장을 유지하여 다음 분석 템포를 가속함
                    for _ in range(20):
                        frame_sequence.popleft()
            
    except WebSocketDisconnect:
        print("❌ 핸드폰 앱과의 연결 종료")
    except Exception as e:
        print(f"❌ 서버 에러: {e}")