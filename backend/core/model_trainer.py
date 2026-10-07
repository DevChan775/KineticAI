import os
import pandas as pd
import numpy as np
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout, Masking
from keras.preprocessing.sequence import pad_sequences
from keras.utils import to_categorical
from keras.optimizers import Adam
from keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib 

# 파일 경로 설정    
BASE_DIR = os.path.dirname(__file__)
CSV_PATH = os.path.join(BASE_DIR, "exercise_dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "kinetic_lstm_model.keras")

print("🚀 CSV 데이터를 읽어와 LSTM 학습 준비를 시작합니다...")

# 1. 데이터 불러오기 및 그룹화
df = pd.read_csv(CSV_PATH)
df['seq_id'] = df['file_name'] + "_" + df['view_name']
df['target_class'] = df['exercise'] + "_" + df['label'].astype(str)

scaler = MinMaxScaler()
coord_cols = df.iloc[:, 7:].select_dtypes(include=['number']).columns
df[coord_cols] = scaler.fit_transform(df[coord_cols])

sequences = []
labels = []

for seq_id, group in df.groupby('seq_id'):
    coords_scaled = group[coord_cols].values
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
    LSTM(32, return_sequences=True),
    Dropout(0.3),
    LSTM(16),
    Dropout(0.3),
    Dense(len(encoder.classes_), activation='softmax')
])

optimizer = Adam(learning_rate=0.001)
model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])


early_stopping = EarlyStopping(monitor='val_loss', patience=5, verbose=1)
# val_loss가 가장 낮을 때의 모델만 덮어쓰기하여 저장 (save_best_only = True)
model_checkpoint = ModelCheckpoint(MODEL_PATH, monitor='val_loss', save_best_only=True, verbose=1)

# 5. 훈련 시작
print("🧠 인공지능 훈련을 시작합니다...")
history = model.fit(
    X_train, y_train, 
    epochs=30, 
    batch_size=32, 
    validation_data=(X_test, y_test),
    callbacks=[early_stopping, model_checkpoint]  
)

# 스케일러/인코더 저장
joblib.dump(scaler, os.path.join(BASE_DIR, "scaler.pkl"))
joblib.dump(encoder, os.path.join(BASE_DIR, "encoder.pkl")) 

print(f"🎉 학습 완료! 모델 및 전처리 파일이 저장되었습니다.")