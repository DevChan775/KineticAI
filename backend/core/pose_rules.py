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
        self._ready_for_exercise = True
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
            return {
                "status": "error",
                "error_code": "waist_bend",
                "message": "허리가 처졌습니다",
                "rep_number": current_rep,
                }

        if elbow_angle is None:
            return {
                "status": "error",
                "error_code": "landmark_missing",
                "message": "팔 각도를 측정할 수 없습니다",
                "rep_number": current_rep,
                }
  
        if elbow_angle <= 90:
            self._down_completed = True
            self._ready_for_exercise = False
            return {
                "status": "in_progress",
                "error_code": None,
                "message": "최저점 도달, 올라오세요",
                "rep_number": current_rep,
            }

        if elbow_angle > 90 and elbow_angle < 150:
            if self._down_completed:
                return {
                    "status": "in_progress",
                    "error_code": None,
                    "message": "팔을 완전히 펴세요",
                    "rep_number": current_rep,
                    }
            else:
                return {
                    "status": "in_progress",
                    "error_code": None,
                    "message": "팔을 완전히 굽히세요",
                    "rep_number": current_rep,
                    }

        

        # TODO: elbow_angle이 90 < elbow_angle < 150 정의하기 (반환값: {"status": "in_progress", ...})
        if elbow_angle >= 150:
            if self._down_completed:
                self._down_completed = False
                self._ready_for_exercise = True
                return {
                     "status": "count_success",
                     "error_code": None,
                     "message": "COUNT_SUCCESS",
                     "rep_number": current_rep,
                     }
                
            if not self._down_completed and not self._ready_for_exercise:
                return {
                      "status": "error",
                      "error_code": "insufficient_depth",
                      "message": "팔을 완전히 펴세요",
                      "rep_number": current_rep,
                      }

            if self._ready_for_exercise:
                return {
                      "status": "in_progress",
                      "error_code": None,
                      "message": "운동 진행중입니다",
                      "rep_number": current_rep,
                      }


    def evaluate_sequence(self, landmarks_sequence: list, rep_number: int = 1):
        """60프레임 랜드마크 시퀀스를 평가하고 rep 단위의 모든 중복 없는 에러 또는 성공 결과를 반환한다."""
        self._down_completed = False
        self._ready_for_exercise = True

        has_valid_frame = False
        is_success = False
        errors = []
        seen_error_codes = set()

        for landmarks in landmarks_sequence:
            if not landmarks:
                continue

            has_valid_frame = True
            result = self.evaluate(landmarks, rep_number)
            status = result.get("status")

            if status == "error":
                error_code = result.get("error_code")
                if error_code not in seen_error_codes:
                    seen_error_codes.add(error_code)
                    errors.append({
                        "error_code": error_code,
                        "message": result.get("message"),
                    })
            elif status == "count_success":
                is_success = True

        if not has_valid_frame:
            return {
                "status": "idle",
                "rep_number": rep_number,
                "errors": [],
                "message": "no_landmarks",
            }


        if errors:
            return {
                "status": "error",
                "rep_number": rep_number,
                "errors": errors,  
                "message": errors[0]["message"],  
            }


        if is_success:
            return {
                "status": "count_success",
                "rep_number": rep_number,
                "errors": [],
                "message": "COUNT_SUCCESS",
            }


        return {
            "status": "error",
            "rep_number": rep_number,
            "errors": [{"error_code": "insufficient_depth", "message": "팔을 충분히 굽혔다 펴세요"}],
            "message": "팔을 충분히 굽혔다 펴세요",
        }