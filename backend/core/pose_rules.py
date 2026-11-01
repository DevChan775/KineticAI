import math
import time
from typing import Iterable, List, Optional, Sequence, Tuple, Union


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
        self.count = 0
        self._last_count_time = None
        self._down_completed = False

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

    def evaluate(self, landmarks, timestamp=None):
        """현재 프레임의 랜드마크를 기반으로 푸시업 상태를 평가한다."""
        if timestamp is None:
            timestamp = time.monotonic()

        if not landmarks:
            return self.count, ""

        elbow_angle = self._get_elbow_angle(landmarks)
        torso_angle = self._get_torso_angle(landmarks)

        if torso_angle is not None and torso_angle < 160:
            return self.count, "허리가 처졌습니다"

        if elbow_angle is None:
            return self.count, "팔 각도를 측정할 수 없습니다"

        # 푸시업은 팔이 많이 구부러진 상태(하강) -> 팔이 편 상태(상승) 순서로 한 회가 끝난다.
        if elbow_angle <= 90:
            self._down_completed = True
            return self.count, "팔을 내리고 있습니다. 몸을 더 낮게 내려가세요"

        if elbow_angle >= 150:
            if self._down_completed:
                if self._last_count_time is None or (timestamp - self._last_count_time) >= 0.6:
                    self.count += 1
                    self._last_count_time = timestamp
                    self._down_completed = False
                    return self.count, "COUNT_SUCCESS"
                self._down_completed = False
                return self.count, "한 번 완료되었습니다"
            return self.count, "팔을 완전히 펴세요"

        self._down_completed = False
        return self.count, "팔을 더 편하게 펴세요"

    def evaluate_pushup(self, landmarks, timestamp=None):
        return self.evaluate(landmarks, timestamp=timestamp)


def evaluate_pushup(landmarks, analyzer=None):
    """편의 함수: 푸시업 분석을 한 번 수행하고 (count, feedback_msg)를 반환."""
    if analyzer is None:
        analyzer = PushUpAnalyzer()
    return analyzer.evaluate(landmarks)
