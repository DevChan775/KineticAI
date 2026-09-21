# backend/api/video_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import cv2
import numpy as np
import base64

router = APIRouter()

@router.websocket("/ws/video")
async def websocket_video_endpoint(websocket: WebSocket):
    """
    핸드폰 앱과 실시간으로 데이터를 주고받는 웹소켓 통로입니다.
    """
    await websocket.accept()
    print("✅ 핸드폰 앱과 실시간 연결이 성공했습니다!")
    
    try:
        while True:
            # 1. 핸드폰에서 보낸 영상 데이터(Base64 문자열)를 받음
            data = await websocket.receive_text()
            
            # 2. 받은 문자열을 다시 이미지(OpenCV 포맷)로 변환
            img_data = base64.b64decode(data)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # TEST: 현재는 영상이 잘 들어오는지 확인하기 위해 서버 쪽 화면에 띄움
            # 실제 서비스 배포 시에는 cv2.imshow를 제거해야 합니다.
            if frame is not None:
                cv2.imshow("Server View: Live from App", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # 
            # TODO: MediaPipe 관절 추출 -> LSTM 분석 -> 피드백 텍스트 생성 코드
            
            # 3. 분석이 끝났다고 가정하고 핸드폰으로 결과를 돌려보냄
            await websocket.send_json({"status": "분석중", "feedback": "자세가 좋습니다!"})
            
    except WebSocketDisconnect:
        print("❌ 핸드폰 앱과의 연결이 끊어졌습니다.")
    finally:
        cv2.destroyAllWindows()