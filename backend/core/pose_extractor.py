import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose

def extract_keypoints(video_path: str):
    """
    저장된 영상을 불러와 매 프레임마다 33개의 관절 3D 좌표(x, y, z)를 추출합니다.
    """
    # 1. 영상을 재생할 준비 (cap에는 영상의 중요한 정보들만 간단하게 정리함)
    cap = cv2.VideoCapture(video_path)
    all_frames_data = [] # 모든 프레임의 좌표를 모아둘 바구니

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break # 영상이 끝나면 멈춤

            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 성능 향상을 위해 이미지 쓰기 불가 모드로 설정 후 모델에 통과
            image_rgb.flags.writeable = False
            results = pose.process(image_rgb)

            # 5. 추론된 33개의 3D 좌표를 바구니에 담기
            if results.pose_world_landmarks:
                frame_keypoints = []
                for landmark in results.pose_world_landmarks.landmark:
                    frame_keypoints.append({
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                        "visibility": landmark.visibility # 눈에 보이는 값인지, 즉 ai가 얼마나 정확하게 판단한 값인지를 의미
                    })
                all_frames_data.append(frame_keypoints)

    # 6. 영상 닫기
    cap.release()
    return all_frames_data