import math
import time
from typing import Any, Dict, Optional


def calculate_angle(a, b, c):
    """세 점 a, b, c를 받아 b를 기준으로 사잇각(0~180도)을 계산"""
    ax, ay = a
    bx, by = b
    cx, cy = c

    ba_x = ax - bx
    ba_y = ay - by
    bc_x = cx - bx
    bc_y = cy - by

    dot = ba_x * bc_x + ba_y * bc_y
    mag_ba = math.hypot(ba_x, ba_y)
    mag_bc = math.hypot(bc_x, bc_y)

    if mag_ba == 0 or mag_bc == 0:
        return 0.0

    cos_theta = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    angle = math.degrees(math.acos(cos_theta))
    return max(0.0, min(180.0, angle))


class PushUpAnalyzer:
    """MediaPipe 랜드마크 기반 푸시업 분석기"""

    def __init__(self):
        self._down_completed = False
        self.error_history: list[Dict[str, Any]] = []
        self.last_error: Optional[Dict[str, Any]] = None
        self._last_error_signature: Optional[tuple] = None

    @staticmethod
    def _to_xy(point):
        if point is None:
            return None
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            return float(point[0]), float(point[1])
        if isinstance(point, dict):
            if "x" in point and "y" in point:
                return float(point["x"]), float(point["y"])
            if "X" in point and  "Y" in point:
                return float(point["X"]), float(point["Y"])
        if hasattr(point, "x") and hasattr(point, "y"):
            return float(point.x), float(point.y)
        return None

    def _get_point(self, landmarks, index):
        if not landmarks or index >= len(landmarks):
            return None
        return self._to_xy(landmarks[index])

    def _log_error(self, error_code: str, message: str, rep_number: Optional[int] = None):
        rep_number = 1 if rep_number is None else rep_number
        signature = (rep_number, error_code)
        if self._last_error_signature == signature:
            return self.last_error

        entry = {
            "exercise": "push_up",
            "rep_number": rep_number,
            "error_code": error_code,
            "message": message,
            "timestamp": time.time(),
        }
        self.error_history.append(entry)
        self.last_error = entry
        self._last_error_signature = signature
        print(f"[pushup_error] rep={rep_number} code={error_code} message={message}")
        return entry

    def _get_elbow_angle(self, landmarks):
        left_shoulder = self._get_point(landmarks, 11)
        left_elbow = self._get_point(landmarks, 13)
        left_wrist = self._get_point(landmarks, 15)

        right_shoulder = self._get_point(landmarks, 12)
        right_elbow = self._get_point(landmarks, 14)
        right_wrist = self._get_point(landmarks, 16)

        angles = []

        if all(v is not None for v in (left_shoulder, left_elbow, left_wrist)):
            angles.append(calculate_angle(left_shoulder, left_elbow, left_wrist))
        if all(v is not None for v in (right_shoulder, right_elbow, right_wrist)):
            angles.append(calculate_angle(right_shoulder, right_elbow, right_wrist))

        if not angles:
            return None
        return min(angles)

    def _get_torso_angle(self, landmarks):
        left_shoulder = self._get_point(landmarks, 11)
        right_shoulder = self._get_point(landmarks, 12)
        left_hip = self._get_point(landmarks, 23)
        right_hip = self._get_point(landmarks, 24)
        left_ankle = self._get_point(landmarks, 27)
        right_ankle = self._get_point(landmarks, 28)

        shoulder = None
        hip = None
        ankle = None

        if all(v is not None for v in (left_shoulder, right_shoulder)):
            shoulder = (
                (left_shoulder[0] + right_shoulder[0]) / 2,
                (left_shoulder[1] + right_shoulder[1]) / 2,
            )
        if all(v is not None for v in (left_hip, right_hip)):
            hip = (
                (left_hip[0] + right_hip[0]) / 2,
                (left_hip[1] + right_hip[1]) / 2,
            )
        if all(v is not None for v in (left_ankle, right_ankle)):
            ankle = (
                (left_ankle[0] + right_ankle[0]) / 2,
                (left_ankle[1] + right_ankle[1]) / 2,
            )

        if all(v is not None for v in (shoulder, hip, ankle)):
            return calculate_angle(shoulder, hip, ankle)
        return None

    def evaluate(self, landmarks, rep_number: int = 1):
        """현재 프레임의 랜드마크를 기반으로 푸시업 상태를 평가한다."""

        if not landmarks:
            return {"status": "idle", "message": "no_landmarks", "error_code": None, "rep_number": rep_number}

        elbow_angle = self._get_elbow_angle(landmarks)
        torso_angle = self._get_torso_angle(landmarks)
        current_rep = rep_number
        if torso_angle is not None and torso_angle < 160:
            self._log_error("waist_bend", "허리가 처졌습니다", current_rep)
            return {
                "status": "error",
                "error_code": "waist_bend",
                "message": "허리가 처졌습니다",
                "rep_number": current_rep,
                }

        if elbow_angle is None:
            self._log_error("landmark_missing", "팔 각도를 측정할 수 없습니다", current_rep)
            return {
                "status": "error",
                "error_code": "landmark_missing",
                "message": "팔 각도를 측정할 수 없습니다",
                "rep_number": current_rep,
                }
  
        if elbow_angle <= 90:
            self._down_completed = True

        # TODO: elbow_angle이 90 < elbow_angle < 150 정의하기 (반환값: {"status": "in_progress", ...})
        if elbow_angle >= 150:
            if self._down_completed:
                self._down_completed = False
                return {
                     "status": "count_success",
                     "error_code": None,
                     "message": "COUNT_SUCCESS",
                     "rep_number": current_rep,
                     }
                
            # TODO: 60프레임 전체를 다 본 뒤 self._down_completed가 끝까지 False였을 때 한 번만 판정 (처음부터 팔을 피라는 문구 출력 방지)
            return {
                "status": "error",
                "error_code": "insufficient_depth",
                "message": "팔을 완전히 펴세요",
                "rep_number": current_rep,
                }


    def evaluate_sequence(self, landmarks_sequence: list, rep_number: int = 1):
        """60프레임 랜드마크 시퀀스를 순서대로 평가하고 rep 단위 에러를 반환한다."""

        last_result = {
            "status": "idle",
            "error_code": None,
            "message": "no_landmarks",
            "rep_number": rep_number,
        }
        first_error = None
        has_valid_frame = False

        
        for landmarks in landmarks_sequence:
            if not landmarks:
               continue

            has_valid_frame = True
            result = self.evaluate(landmarks, rep_number)

            result = dict(result)
            
            result["rep_number"] = rep_number

            if result.get("status") == "error" and first_error is None:
                first_error = dict(result)

            last_result = result

        if not has_valid_frame:
            return {
                    "status": "idle",
                    "error_code": None,
                    "message": "no_landmarks",
                    "rep_number": rep_number,
                    }

        return first_error or last_result
        