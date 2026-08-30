import pandas as pd
import os

# 1. 파일 경로 자동 설정
# 현재 이 파이썬 코드가 있는 위치를 파악한 뒤, 데이터 파일의 위치를 연결
current_folder = os.path.dirname(__file__)
csv_file_path = os.path.join(current_folder, "exercise_dataset.csv")

try:
    df = pd.read_csv(csv_file_path)
    print("✅ 데이터 불러오기 성공!")
    print("데이터 미리보기:\n", df.head(), "\n")
    
    y = df['Label']
    X = df.drop('Label', axis=1)
    
    print("✅ 문제지와 정답지 분리 완료!")
    print("문제지(X)의 형태(데이터 개수, 관절 각도 수):", X.shape)
    print("정답지(y)의 형태(정답 개수):", y.shape)

except FileNotFoundError:
    print("오류: 파일을 찾을 수 없습니다. 'exercise_dataset.csv' 파일이 올바른 위치에 있는지 확인해 주세요.")
except KeyError:
    print("오류: 데이터에 'Label' 열이 없습니다. 엑셀에서 정답 열의 이름이 정확히 무엇인지 확인해 주세요.")