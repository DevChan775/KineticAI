import os
import pandas as pd
import numpy as np
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from sklearn.preprocessing import LabelEncoder
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
# '운동이름_정답여부' 형태로 정답지(예: pull_up_1)를 만듭니다.
df['target_class'] = df['exercise'] + "_" + df['label'].astype(str)

sequences = []
labels = []

# 각 영상(seq_id)별로 관절 좌표들만 묶어서 하나의 시퀀스(흐름)로 만듭니다.
for seq_id, group in df.groupby('seq_id'):
    # 6번 열(Nose_x)부터 끝까지가 48개의 X, Y 좌표입니다.
    coords = group.iloc[:, 6:].values.tolist() 
    sequences.append(coords)
    # 해당 묶음의 정답지를 저장합니다.
    labels.append(group['target_class'].iloc[0])

# 2. 데이터 길이 맞추기 (패딩)
MAX_FRAMES = 100 # 최대 프레임 길이 (약 3~4초 분량, 필요시 조절 가능)
X = pad_sequences(sequences, maxlen=MAX_FRAMES, padding='post', dtype='float32')

# 3. 정답지(텍스트)를 인공지능이 이해하는 숫자로 변환
encoder = LabelEncoder()
y_encoded = encoder.fit_transform(labels)
y_categorical = to_categorical(y_encoded)

X_train, X_test, y_train, y_test = train_test_split(X, y_categorical, test_size=0.2, random_state=42)

print(f"✅ 학습 데이터 준비 완료! (총 {len(X)}개 영상, {len(encoder.classes_)}개 운동 상태)")

# 4. LSTM 인공지능 모델 뼈대 조립
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(MAX_FRAMES, 48)),
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(len(encoder.classes_), activation='softmax')
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# 5. 본격적인 훈련 시작
print("🧠 인공지능 훈련을 시작합니다. (데이터 양에 따라 시간이 다소 소요됩니다)...")
history = model.fit(X_train, y_train, epochs=30, batch_size=32, validation_data=(X_test, y_test))

# 6. 완성된 인공지능 뇌(모델) 저장
model.save(MODEL_PATH)
print(f"🎉 학습 완료! 훈련된 인공지능이 '{MODEL_PATH}'에 안전하게 저장되었습니다.")