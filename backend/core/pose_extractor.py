import os
import json
import csv

# 1. 24개의 관절 포인트 이름
KEYPOINTS = [
    "Nose", "Left Eye", "Right Eye", "Left Ear", "Right Ear",
    "Left Shoulder", "Right Shoulder", "Left Elbow", "Right Elbow",
    "Left Wrist", "Right Wrist", "Left Hip", "Right Hip",
    "Left Knee", "Right Knee", "Left Ankle", "Right Ankle",
    "Neck", "Left Palm", "Right Palm", "Back", "Waist",
    "Left Foot", "Right Foot"
]

# 2. 파일 경로 설정
BASE_DIR = os.path.dirname(__file__)
DATASET_DIR = os.path.join(BASE_DIR, "lstm_dataset")
OUTPUT_CSV = os.path.join(BASE_DIR, "exercise_dataset.csv")

# 3. 장부 첫 줄(헤더)에 error_conditions(구체적 오답 사유) 열을 추가합니다.
csv_headers = ["file_name", "view_name", "exercise", "label", "condition_code", "frame_num", "error_conditions"]
for kp in KEYPOINTS:
    csv_headers.extend([f"{kp}_x", f"{kp}_y"])

print("🚀 5개 다각도 카메라 관절 데이터 및 [오답 사유(Conditions)] 추출을 시작합니다...")

with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(csv_headers)
    
    for folder_name in os.listdir(DATASET_DIR):
        folder_path = os.path.join(DATASET_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
            
        exercise = folder_name.replace("_correct", "").replace("_incorrect", "")
        label = 1 if "correct" in folder_name and "incorrect" not in folder_name else 0
        
        for condition_code in os.listdir(folder_path):
            condition_path = os.path.join(folder_path, condition_code)
            if not os.path.isdir(condition_path):
                continue
                
            for file_name in os.listdir(condition_path):
                if not file_name.endswith(".json"):
                    continue
                    
                file_path = os.path.join(condition_path, file_name)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # --- [추가된 핵심 로직: Conditions 추출] ---
                    error_reasons = [] # 틀린 이유들을 담을 빈 바구니
                    
                    # type_info 안의 conditions 배열을 안전하게 가져옵니다.
                    type_info = data.get("type_info", {})
                    conditions_list = type_info.get("conditions", [])
                    
                    # 조건들을 하나씩 확인하면서 value가 False인 것의 이름만 바구니에 담습니다.
                    for cond in conditions_list:
                        if cond.get("value") is False:
                            error_reasons.append(cond.get("condition", "").strip())
                    
                    # 바구니에 담긴 이유들을 파이프(|) 기호로 묶어서 하나의 텍스트로 만듭니다.
                    # 만약 정답(correct) 영상이라서 틀린 이유가 없다면 '정답'이라고 기록합니다.
                    if error_reasons:
                        error_conditions_str = "|".join(error_reasons)
                    else:
                        error_conditions_str = "정답"
                    # -------------------------------------------
                        
                    frames = data.get('frames', [])
                    for frame_idx, frame in enumerate(frames):
                        
                        # view1부터 view5까지 5개 카메라를 모두 순회하며 추출합니다.
                        for view_key in ['view1', 'view2', 'view3', 'view4', 'view5']:
                            view_data = frame.get(view_key, {})
                            pts = view_data.get('pts', {})
                            
                            # 만약 특정 카메라 영상이 비어있다면 조용히 건너뜁니다.
                            if not pts:
                                continue
                                
                            # 파일 이름, 카메라 번호와 함께 우리가 추출한 오답 사유(error_conditions_str)도 장부에 적어줍니다.
                            row_data = [file_name, view_key, exercise, label, condition_code, frame_idx, error_conditions_str]
                            
                            for kp in KEYPOINTS:
                                x = pts.get(kp, {}).get("x", 0)
                                y = pts.get(kp, {}).get("y", 0)
                                row_data.extend([x, y])
                                
                            writer.writerow(row_data)
                            
                except Exception as e:
                    # 파일 읽기 중 에러가 나면 그냥 넘어갑니다.
                    pass

print(f"✅ 추출 완료! 완벽한 체크리스트 데이터가 포함된 {OUTPUT_CSV} 파일이 생성되었습니다.")