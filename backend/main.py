from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="KineticAI Backend API",
    description="영상 기반 생체역학 운동 분석 및 맞춤형 코칭 제공 서버",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 주의: 실무 운영 단계에서는 "*" 대신 실제 앱의 주소로 제한해야 합니다.
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST 등 모든 HTTP 통신 메서드 허용
    allow_headers=["*"],
)

# [API] 서버 상태 확인(Health Check) 엔드포인트
# 프론트엔드에서 서버가 죽지 않고 잘 켜져 있는지 확인하기 위해 가장 먼저 호출해보는 기본 주소입니다.
@app.get("/")
async def root_health_check():
    """
    서버의 정상 구동 여부를 반환합니다.
    """
    return {
        "status": "ok", 
        "message": "KineticAI 서버가 정상적으로 실행 중입니다."
    }