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
import joblib 

# 파일 경로 설정
BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "exercise_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "kinetic_lstm_model.h5")

print("🚀 CSV 데이터를 읽어와 LSTM 학습 준비를 시작합니다...")

# 1. 데이터 불러오기 및 그룹화
df = pd.read_csv(CSV_PATH)
df['seq_id'] = df['file_name'] + "_" + df['view_name']
df['target_class'] = df['exercise'] + "_" + df['label'].astype(str)

sequences = []
labels = []

# 정규화를 위한 스케일러 준비
scaler = MinMaxScaler()

for seq_id, group in df.groupby('seq_id'):
    coords = group.iloc[:, 7:].select_dtypes(include=['number']).values
    coords_scaled = scaler.fit_transform(coords)
    sequences.append(coords_scaled.tolist())
    labels.append(group['target_class'].iloc[0])

# 프레임 길이를 60으로 단축
MAX_FRAMES = 60 

# 패딩 적용
X = pad_sequences(sequences, maxlen=MAX_FRAMES, padding='post', dtype='float32')

encoder = LabelEncoder()
y_encoded = encoder.fit_transform(labels)
y_categorical = to_categorical(y_encoded)

X_train, X_test, y_train, y_test = train_test_split(X, y_categorical, test_size=0.2, random_state=42)

print(f"✅ 학습 데이터 준비 완료! (총 {len(X)}개 영상, {len(encoder.classes_)}개 운동 상태)")

# 4. LSTM 모델 조립
model = Sequential([
    Masking(mask_value=0.0, input_shape=(MAX_FRAMES, 48)), 
    LSTM(64, return_sequences=True),
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(len(encoder.classes_), activation='softmax')
])

optimizer = Adam(learning_rate=0.001)
model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])

# 5. 훈련 시작
print("🧠 인공지능 훈련을 시작합니다...")
history = model.fit(X_train, y_train, epochs=30, batch_size=32, validation_data=(X_test, y_test))

# 6. 모델 및 스케일러/인코더 저장
model.save(MODEL_PATH)
joblib.dump(scaler, os.path.join(BASE_DIR, "scaler.pkl"))
joblib.dump(encoder, os.path.join(BASE_DIR, "encoder.pkl"))

print(f"🎉 학습 완료! 모델 및 전처리 파일이 저장되었습니다.")