from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import video_router 

app = FastAPI(
    title="KineticAI Backend API",
    description="영상 기반 생체역학 운동 분석 및 맞춤형 코칭 제공 서버",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

app.include_router(video_router.router, prefix="/api/video", tags=["Video"])

@app.get("/")
async def root_health_check():
    """
    서버의 정상 구동 여부를 반환합니다.
    """
    return {
        "status": "ok", 
        "message": "KineticAI 서버가 정상적으로 실행 중입니다."
    }