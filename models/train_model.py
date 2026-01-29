# 층간소음 종류를 분류하는 AI 모델 학습 스크립트 (실제 데이터 기반)
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import tensorflow as tf
from tensorflow.keras.layers import Input, Conv2D, MaxPooling2D, Flatten, Dense, Dropout, Concatenate
from tensorflow.keras.models import Model
import joblib

# 1. 실제 데이터 기반으로 생성된 데이터셋 불러오기
try:
    df = pd.read_csv("real_noise_data.csv")
except FileNotFoundError:
    print("❌ 'real_noise_data.csv' 파일을 찾을 수 없습니다.")
    print("먼저 'labels.csv' 파일을 작성한 후, 'build_dataset.py'를 실행하여 데이터셋을 생성해주세요.")
    exit()

# 문자열로 된 리스트 데이터를 실제 수치 데이터로 변환
def str_to_list(s):
    import json
    return np.array(json.loads(s))

print(f"총 {len(df)}개의 실제 데이터 샘플로 학습을 준비합니다...")

X_vibration = np.stack(df['vibration_sample'].apply(str_to_list))
# Pad/truncate vibration data to a fixed length, e.g., 50
fixed_vib_length = 50
X_vibration_padded = np.array([np.pad(v, (0, fixed_vib_length - len(v)), 'constant') if len(v) < fixed_vib_length else v[:fixed_vib_length] for v in X_vibration])

X_sound_mfcc = np.stack(df['sound_sample'].apply(str_to_list))
y = df['label']

# 2. 전처리 (정답 라벨 수치화)
le = LabelEncoder()
y_encoded = le.fit_transform(y)

# CNN 입력을 위해 MFCC 데이터를 2D 이미지 형태로 Reshape
n_mfcc = X_sound_mfcc.shape[1]
n_frames = X_sound_mfcc.shape[2]
X_sound_reshaped = X_sound_mfcc.reshape(-1, n_mfcc, n_frames, 1)

# 진동 데이터는 StandardScaler로 정규화
scaler = StandardScaler()
X_vibration_scaled = scaler.fit_transform(X_vibration_padded)


X_train_sound, X_test_sound, X_train_vibration, X_test_vibration, y_train, y_test = train_test_split(
    X_sound_reshaped, X_vibration_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)

# 3. 모델 설계 (CNN과 DNN을 결합한 멀티모달 구조)

# --- CNN 분기 (소리 특징 처리) ---
sound_input = Input(shape=(n_mfcc, n_frames, 1), name='sound_input')
x = Conv2D(32, (3, 3), activation='relu', padding='same')(sound_input)
x = MaxPooling2D((2, 2))(x)
x = Dropout(0.25)(x)
x = Conv2D(64, (3, 3), activation='relu', padding='same')(x)
x = MaxPooling2D((2, 2))(x)
x = Dropout(0.25)(x)
x = Flatten()(x)
sound_output = Dense(32, activation='relu')(x)

# --- DNN 분기 (진동 특징 처리) ---
vibration_input = Input(shape=(X_vibration_scaled.shape[1],), name='vibration_input')
y = Dense(16, activation='relu')(vibration_input)
vibration_output = Dense(8, activation='relu')(y)

# --- 특징 결합 및 최종 분류 ---
combined = Concatenate()([sound_output, vibration_output])
z = Dense(64, activation='relu')(combined)
z = Dropout(0.5)(z)
output = Dense(len(le.classes_), activation='softmax', name='output')(z)

model = Model(inputs=[sound_input, vibration_input], outputs=output)

model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
model.summary()

# 4. 학습 시작
print("\n🚀 새로운 CNN 기반 AI 모델 재학습을 시작합니다...")
history = model.fit(
    [X_train_sound, X_train_vibration], 
    y_train, 
    epochs=30, 
    batch_size=16, 
    validation_data=([X_test_sound, X_test_vibration], y_test),
    verbose=2
)

# 5. 모델 및 Scaler 저장
model.save("noise_model_v2.h5")
np.save("classes_v2.npy", le.classes_)
joblib.dump(scaler, 'vibration_scaler_v2.joblib') # Save the fitted scaler

print("\n✅ 재학습 완료! 'noise_model_v2.h5', 'classes_v2.npy', 'vibration_scaler_v2.joblib' 파일이 생성되었습니다.")
print("새로운 모델을 적용하려면, ai_model.py의 load_ai_model 함수에서 관련 파일명을 v2로 변경해주세요.")