import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from keras.models import load_model

# 1. FastAPI 라우터(현관문) 생성
router = APIRouter()

# 2. 통합 AI 모델 로드 (서버 켜질 때 한 번만)
print("🧠 통합 AI 모델을 서버 메모리에 로드합니다...")
model = load_model("kinetic_lstm_model.h5")

CLASSES = [
    "dips_0", "dips_1", "plank_0", "plank_1",
    "pull_up_0", "pull_up_1", "push_up_0", "push_up_1",
    "side_lunge_0", "side_lunge_1"
]

# 3. 앱에서 보내올 데이터의 형태(봉투) 정의
class VideoRequest(BaseModel):
    selected_exercise: str  # 예: 'pull_up'
    video_coordinates: list # 앱에서 추출해 보낸 100x48 좌표 리스트

# 4. 진짜 웹 통신 라우터 (앱에서 여기로 데이터를 쏩니다)
@router.post("/analyze")
async def analyze_exercise_video(request: VideoRequest):
    try:
        # 받은 데이터 꺼내기
        exercise = request.selected_exercise
        coords = request.video_coordinates
        
        # 3차원 텐서로 변환 (1, 100, 48)
        input_data = np.array([coords], dtype='float32')

        # AI 예측 실행
        predictions = model.predict(input_data)[0]

        # 사용자 선택에 맞춘 필터링
        target_correct = f"{exercise}_1"
        target_incorrect = f"{exercise}_0"
        
        correct_prob = 0.0
        incorrect_prob = 0.0

        for i, class_name in enumerate(CLASSES):
            if class_name == target_correct:
                correct_prob = predictions[i]
            elif class_name == target_incorrect:
                incorrect_prob = predictions[i]

        total_prob = correct_prob + incorrect_prob
        if total_prob < 0.1:
            return {"status": "error", "message": "엉뚱한 동작입니다. 다시 촬영해주세요."}

        # 최종 결과 앱으로 전송
        if correct_prob > incorrect_prob:
            return {"status": "success", "message": f"완벽한 {exercise} 자세입니다!"}
        else:
            return {"status": "warning", "message": f"틀린 {exercise} 자세입니다. 교정해주세요."}

    except Exception as e:
        # 에러 발생 시 앱이 튕기지 않도록 에러 메시지 전송
        raise HTTPException(status_code=500, detail=str(e))