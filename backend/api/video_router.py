import shutil
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Form 

UPLOAD_DIR = Path("data/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter() 

@router.post("/upload")
async def upload_exercise_video(
    exercise_type: str = Form(...), 
    file: UploadFile = File(...)):
    """
    사용자가 선택한 운동 종목과 촬영한 영상 파일을 동시에 받아 서버에 저장합니다.
    """
    if not file.filename.endswith((".mp4", ".mov", ".avi")):
        raise HTTPException(
            status_code=400, 
            detail="지원하지 않는 파일 형식입니다. 동영상 파일(.mp4, .mov, .avi)만 업로드해주세요."
        )
    
    file_path = UPLOAD_DIR / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 중 오류가 발생했습니다: {str(e)}")
    
    print(f"수신된 운동 종목: {exercise_type}")
    
    return {
        "status": "success",
        "exercise": exercise_type,
        "filename": file.filename,
        "message": f"[{exercise_type}] 영상이 성공적으로 업로드되었습니다. 다음 단계를 준비합니다."
    }