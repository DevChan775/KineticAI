import os
import json
import shutil

# 1. 추출할 타겟 운동 (풀업, 딥스)
TARGET_EXERCISES = {
    "풀업": "pull_up",
    "딥스": "dips"
}

# 2. 경로 설정 (기존과 동일한 최상위 라벨링 폴더 경로)
# 기구_01 ~ 기구_04 폴더들이 위치한 상위 폴더 경로입니다.
SOURCE_DIR = r"C:\Users\USER\OneDrive\바탕 화면\visual studio\KineticAI_project\backend\core\exercise_dataset\1.Training\라벨링데이터\data_Labeling_new_220128"
TARGET_DIR = r"C:\Users\USER\OneDrive\바탕 화면\visual studio\KineticAI_project\backend\core\lstm_dataset"

print("🚀 기구 운동(풀업, 딥스)의 Condition 기반 정밀 분류를 시작합니다...")

copy_count = 0

# os.walk가 기구_01 ~ 기구_04 내부의 중첩 폴더들을 전부 탐색합니다.
for root, dirs, files in os.walk(SOURCE_DIR):
    for file in files:
        # 3D 데이터는 제외하고 일반 2D JSON 파일만 처리합니다.
        if file.endswith(".json") and not file.endswith("-3d.json"):
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                exercise_name_kr = data['type_info']['exercise']
                condition_code = data['type_info']['key'] 
                conditions = data['type_info']['conditions']
                
                # 세부 평가 조건 중 하나라도 false가 있는지 검사합니다.
                is_correct = True
                for cond in conditions:
                    if cond.get('value') is False:
                        is_correct = False
                        break # 하나라도 틀리면 오답 판정
                
                # 풀업 또는 딥스 종목인지 확인합니다.
                for kr_name, en_name in TARGET_EXERCISES.items():
                    if kr_name in exercise_name_kr:
                        
                        # 판정 결과에 맞춰 저장 폴더를 분기합니다.
                        if is_correct:
                            dataset_folder = f"{en_name}_correct"
                        else:
                            dataset_folder = f"{en_name}_incorrect"
                            
                        # 최종 목적지: lstm_dataset / pull_up_correct / 상태코드 / 파일.json
                        final_target_dir = os.path.join(TARGET_DIR, dataset_folder, condition_code)
                        os.makedirs(final_target_dir, exist_ok=True)
                        
                        target_path = os.path.join(final_target_dir, file)
                        shutil.copy(file_path, target_path)
                        copy_count += 1
                        break
                        
            except Exception as e:
                # 손상되었거나 형식이 다른 파일은 무시하고 진행합니다.
                pass

print(f"✅ 분류 완료! 총 {copy_count}개의 풀업/딥스 데이터가 정리되었습니다.")