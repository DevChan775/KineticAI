from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import numpy as np
import base64
import json
import os
import time
import joblib
import tensorflow as tf
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from core.pose_rules import PushUpAnalyzer

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CORE_DIR = os.path.join(BASE_DIR, "core")

model_asset_path = os.path.join(CORE_DIR, "pose_landmarker_full.task")

if not os.path.exists(model_asset_path):
    print(f"⚠️ 에러: {model_asset_path} 파일이 존재하지 않습니다. 모델 파일을 먼저 다운로드하세요.")

base_options = python.BaseOptions(model_asset_path=model_asset_path)
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    min_pose_detection_confidence=0.3,
    min_pose_presence_confidence=0.3,
    min_tracking_confidence=0.3,
)
detector = vision.PoseLandmarker.create_from_options(options)

model = None
scaler = None
encoder = None
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
    push_up_analyzer = PushUpAnalyzer()
    print("✅ 핸드폰 앱과 실시간 연결 성공!")

    try:
        while True:
            payload = await websocket.receive_text()
            if not payload:
                continue

            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                print("⚠️ 잘못된 JSON 페이로드")
                continue

            rep_number = data.get("rep_number")
            exercise = str(data.get("exercise", "")).strip().lower()
            frames = data.get("frames")

            if not isinstance(rep_number, int) or rep_number < 1:
                print("⚠️ 유효하지 않은 rep_number")
                continue
            if not isinstance(frames, list) or len(frames) != SEQ_LENGTH:
                print(f"⚠️ rep={rep_number}: 프레임 수가 60개가 아닙니다")
                continue

            frame_keypoints = [None] * SEQ_LENGTH
            landmark_sequence = [None] * SEQ_LENGTH
            valid_frame_count = 0
            rep_start_ms = int(time.time() * 1000)

            for frame_index, frame_base64 in enumerate(frames):
                if not isinstance(frame_base64, str):
                    continue

                try:
                    img_data = base64.b64decode(frame_base64, validate=True)
                    np_arr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                    if frame is None:
                        continue

                    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
                    timestamp_ms = rep_start_ms + (frame_index * 1000 // 30)
                    detection_result = detector.detect_for_video(mp_image, timestamp_ms)
                except Exception as exc:
                    print(f"⚠️ rep={rep_number} frame={frame_index}: 디코딩/포즈 추출 실패: {exc}")
                    continue

                if not detection_result.pose_landmarks:
                    continue

                landmarks = detection_result.pose_landmarks[0]

                def get_pt(idx):
                    return [landmarks[idx].x, landmarks[idx].y]

                center_shoulder = [
                    (landmarks[11].x + landmarks[12].x) / 2,
                    (landmarks[11].y + landmarks[12].y) / 2,
                ]
                center_hip = [
                    (landmarks[23].x + landmarks[24].x) / 2,
                    (landmarks[23].y + landmarks[24].y) / 2,
                ]

                neck = center_shoulder
                back = [
                    center_shoulder[0] + (center_hip[0] - center_shoulder[0]) * (1 / 3),
                    center_shoulder[1] + (center_hip[1] - center_shoulder[1]) * (1 / 3),
                ]
                waist = [
                    center_shoulder[0] + (center_hip[0] - center_shoulder[0]) * (2 / 3),
                    center_shoulder[1] + (center_hip[1] - center_shoulder[1]) * (2 / 3),
                ]

                l_palm = [(landmarks[15].x + landmarks[19].x) / 2, (landmarks[15].y + landmarks[19].y) / 2]
                r_palm = [(landmarks[16].x + landmarks[20].x) / 2, (landmarks[16].y + landmarks[20].y) / 2]
                l_foot = [(landmarks[27].x + landmarks[31].x) / 2, (landmarks[27].y + landmarks[31].y) / 2]
                r_foot = [(landmarks[28].x + landmarks[32].x) / 2, (landmarks[28].y + landmarks[32].y) / 2]

                keypoints = []
                keypoints.extend(get_pt(0))   # Nose (x, y)
                keypoints.extend(get_pt(2))   # Left Eye
                keypoints.extend(get_pt(5))   # Right Eye
                keypoints.extend(get_pt(7))   # Left Ear
                keypoints.extend(get_pt(8))   # Right Ear
                keypoints.extend(get_pt(11))  # Left Shoulder
                keypoints.extend(get_pt(12))  # Right Shoulder
                keypoints.extend(get_pt(13))  # Left Elbow
                keypoints.extend(get_pt(14))  # Right Elbow
                keypoints.extend(get_pt(15))  # Left Wrist
                keypoints.extend(get_pt(16))  # Right Wrist
                keypoints.extend(get_pt(23))  # Left Hip
                keypoints.extend(get_pt(24))  # Right Hip
                keypoints.extend(get_pt(25))  # Left Knee
                keypoints.extend(get_pt(26))  # Right Knee
                keypoints.extend(get_pt(27))  # Left Ankle
                keypoints.extend(get_pt(28))  # Right Ankle

                keypoints.extend(neck)
                keypoints.extend(l_palm)
                keypoints.extend(r_palm)
                keypoints.extend(back)
                keypoints.extend(waist)
                keypoints.extend(l_foot)
                keypoints.extend(r_foot)

                frame_keypoints[frame_index] = keypoints # ai 예측 전용
                landmark_sequence[frame_index] = landmarks # 관절 평가 데이터
                valid_frame_count += 1

            if valid_frame_count == 0:
                print(f"⚠️ rep={rep_number}: 추출 가능한 포즈가 없습니다")
                continue

            if None in frame_keypoints:
                print(f"⚠️ rep={rep_number}: 일부 프레임에서 포즈 추출 실패, 누락된 프레임이 있습니다")

            # 누락 프레임은 직전 유효 프레임으로 채워 입력 shape를 유지한다
            padded_keypoints = []
            last_valid_keypoints = np.zeros(48, dtype=np.float32)
            for keypoints in frame_keypoints:
                if keypoints is not None:
                    last_valid_keypoints = np.asarray(keypoints, dtype=np.float32)
                padded_keypoints.append(last_valid_keypoints.copy())

            if model is None or scaler is None or encoder is None:
                print(f"⚠️ rep={rep_number}: 모델이 로드되지 않아 추론을 건너뜁니다")
                continue

            input_data = np.asarray(padded_keypoints, dtype=np.float32)
            if input_data.shape != (SEQ_LENGTH, 48):
                print(f"⚠️ rep={rep_number}: 키포인트 shape={input_data.shape}")
                continue

            input_scaled = scaler.transform(input_data)
            input_final = np.expand_dims(input_scaled, axis=0)

            # 이 rep의 60프레임에 대해 model.predict()는 단 1회만 호출한다.
            prediction = model.predict(input_final, verbose=0)
            class_idx = int(np.argmax(prediction))
            max_prob = float(np.max(prediction))

            if max_prob < 0.50:
                continue

            predicted_label = str(encoder.inverse_transform([class_idx])[0]).strip()
            normalized_name = predicted_label.lower().replace(" ", "_").replace("-", "_")
            if normalized_name.endswith("_correct") or normalized_name.endswith("_incorrect"):
                normalized_name = normalized_name.rsplit("_", 1)[0]

            is_push_up = (
                normalized_name in {"push_up", "pushup"}
                or normalized_name.startswith("push_up")
                or normalized_name.startswith("pushup")
            )

            if not is_push_up:
                continue

            exercise_name = exercise.replace("-", "_").replace(" ", "_")
            if exercise_name not in {"", "push_up", "pushup"}:
                continue

            if landmark_sequence:
                rule_result = push_up_analyzer.evaluate_sequence(landmark_sequence, rep_number=rep_number)

                if rule_result and rule_result.get("status") in {"error", "count_success"}:
                    await websocket.send_text(json.dumps(rule_result))

                # TODO: DB 적재

    except WebSocketDisconnect:
        print("❌ 핸드폰 앱과의 연결 종료")
    except Exception as e:
        print(f"❌ 서버 에러: {e}")