import shutil
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from backend.core.pose_extractor import extract_keypoints 

UPLOAD_DIR = Path("data/videos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter() 

@router.post("/upload")
async def upload_exercise_video(
    exercise_type: str = Form(...), 
    file: UploadFile = File(...)    
):
    
    if not file.filename.endswith((".mp4", ".mov", ".avi")):
        raise HTTPException(
            status_code=400, 
            detail="지원하지 않는 파일 형식입니다. 동영상 파일만 업로드해주세요."
        )
    
    file_path = UPLOAD_DIR / file.filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 중 오류가 발생했습니다: {str(e)}")

    try:
        print(f"[{exercise_type}] 영상 분석을 시작합니다...")
        keypoints = extract_keypoints(str(file_path)) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"관절 추출 중 오류가 발생했습니다: {str(e)}")
    
    return {
        "status": "success",
        "exercise": exercise_type,
        "filename": file.filename,
        "extracted_frames_count": len(keypoints), # 몇 장의 사진에서 관절을 찾았는지 체크
        "message": f"[{exercise_type}] 영상의 관절 데이터 {len(keypoints)}프레임 추출이 완료되었습니다."
    }