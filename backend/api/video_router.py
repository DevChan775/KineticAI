import shutil # 프론트에서 전달 받은 영상을 목적지로 옮긴 수단
from pathlib import Path # 컴퓨터 내의 폴더나 파일 주소를 쉽게 관리하기 위한 도구 
from fastapi import APIRouter, File, UploadFile, HTTPException # 앱과의 통신을 관리하는 FastAPI의 핵심 부품

# [CONFIG] 영상이 저장될 로컬 폴더 경로 설정
# 프론트엔드에서 보낸 영상이 일시적으로 보관될 공간입니다.
UPLOAD_DIR = Path("data/videos") # 앞으로 들어오는 영상은 모두 "data/videos" "주소로 모은다 
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# [API] 영상 업로드 수신 엔드포인트
# 프론트엔드 앱에서 POST 방식으로 영상을 전송하면 이 함수가 실행됩니다.
async def upload_exercise_video(file: UploadFile = File(...)):
    """
    사용자가 촬영한 운동 영상 파일을 받아 서버에 저장합니다.
    """
    # 1. 파일 확장자 검증 (mp4, mov 등 동영상 파일인지 간단히 확인)
    if not file.filename.endswith((".mp4", ".mov", ".avi")):
        raise HTTPException(
            status_code=400, 
            detail="지원하지 않는 파일 형식입니다. 동영상 파일(.mp4, .mov, .avi)만 업로드해주세요."
        )
    
    # 2. 서버 로컬 저장 경로 설정
    file_path = UPLOAD_DIR / file.filename
    
    try:
        # 3. 전송받은 파일을 스트리밍 방식으로 안전하게 저장
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # 확실하지 않음: 파일 저장 중 디스크 용량 부족이나 권한 문제 발생 가능성 대비
        raise HTTPException(status_code=500, detail=f"파일 저장 중 오류가 발생했습니다: {str(e)}")
    
    return {
        "status": "success",
        "filename": file.filename,
        "message": "영상이 성공적으로 업로드되었습니다. 다음 단계(YOLO-Pose 관절 추출)를 준비합니다."
    }