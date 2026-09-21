import os
import pandas as pd
import numpy as np
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout, Masking
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from keras.optimizers import Adam
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split

# 파일 경로 설정
BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "exercise_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "kinetic_lstm_model.h5")

print("🚀 CSV 데이터를 읽어와 LSTM 학습 준비를 시작합니다...")

# 1. 데이터 불러오기 및 그룹화
df = pd.read_csv(CSV_PATH)

# 파일 이름과 카메라 번호를 합쳐서 고유한 영상 묶음 ID를 만듭니다.
df['seq_id'] = df['file_name'] + "_" + df['view_name']

# '운동이름_정답여부' 형태로 정답지(예: pull_up_T)를 만듭니다.
df['target_class'] = df['exercise'] + "_" + df['label'].astype(str)

sequences = []
labels = []

# 정규화를 위한 스케일러 준비
scaler = MinMaxScaler()

for seq_id, group in df.groupby('seq_id'):
    # 문자열 열을 제외하고 숫자 데이터(좌표)만 추출
    coords = group.iloc[:, 7:].select_dtypes(include=['number']).values
    
    # [수정 핵심] 추출한 좌표를 0~1 사이로 스케일링합니다.
    coords_scaled = scaler.fit_transform(coords)
    
    sequences.append(coords_scaled.tolist())
    labels.append(group['target_class'].iloc[0])


MAX_FRAMES = 100 # (약 3~4초 분량)
# 패딩 적용
X = pad_sequences(sequences, maxlen=MAX_FRAMES, padding='post', dtype='float32')

# 정답(라벨) 인코딩 (10개 클래스로 변환)
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(labels)
y_categorical = to_categorical(y_encoded)

X_train, X_test, y_train, y_test = train_test_split(X, y_categorical, test_size=0.2, random_state=42)

print(f"✅ 학습 데이터 준비 완료! (총 {len(X)}개 영상, {len(encoder.classes_)}개 운동 상태)")

# 4. LSTM 인공지능 모델 뼈대 조립
model = Sequential([
    # [수정 핵심] 패딩으로 채워진 0.0 값을 무시하라는 마스크를 씌워줍니다.
    Masking(mask_value=0.0, input_shape=(MAX_FRAMES, 48)), 
    LSTM(64, return_sequences=True),
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(len(encoder.classes_), activation='softmax')
])

# [수정] 학습률(Learning Rate)을 0.001로 명시하여 안정적인 학습 유도
optimizer = Adam(learning_rate=0.001)
model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])

# 5. 본격적인 훈련 시작
print("🧠 인공지능 훈련을 시작합니다. (데이터 양에 따라 시간이 다소 소요됩니다)...")
history = model.fit(X_train, y_train, epochs=30, batch_size=32, validation_data=(X_test, y_test))

# 6. 완성된 인공지능 뇌(모델) 저장
# 참고: 같은 경로, 같은 이름이므로 기존 모델 파일에 덮어쓰기 됩니다.
model.save(MODEL_PATH)
print(f"🎉 학습 완료! 훈련된 인공지능이 '{MODEL_PATH}'에 안전하게 저장되었습니다.")