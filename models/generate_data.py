#데이터 생성기
import numpy as np
import pandas as pd

def generate_noise_dataset(samples_per_class=500):
    dataset = []
    classes = ['Normal', 'Footstep', 'Conversation', 'TV_Music']
    
    for label in classes:
        for _ in range(samples_per_class):
            # 기본 배경 노이즈 생성 (평상시 소음)
            base_vibration = np.random.normal(1.0, 0.05, 50) # Z축 가속도 기준
            base_sound = np.random.normal(0, 0.5, 20)      # MFCC 특징값 기준
            
            if label == 'Footstep':
                # 주기적인 강한 충격 (발망치 패턴)
                base_vibration[25] += np.random.uniform(1.5, 3.0)
                severity = "Red"
            elif label == 'TV_Music':
                # 지속적인 소리 에너지 상승, 진동은 미미함
                base_sound += np.random.uniform(2.0, 5.0)
                severity = "Yellow"
            elif label == 'Conversation':
                # 가변적인 소리 패턴, 진동 없음
                base_sound += np.random.normal(1.0, 2.0, 20)
                severity = "Green"
            else: # Normal
                severity = "Green"
                
            dataset.append({
                "vibration_sample": base_vibration.tolist(),
                "sound_sample": base_sound.tolist(),
                "label": label,
                "severity": severity
            })
            
    df = pd.DataFrame(dataset)
    df.to_csv("noise_learning_data.csv", index=False)
    print(f"✅ 총 {len(df)}개의 프로젝트 맞춤형 학습 데이터가 생성되었습니다. (noise_learning_data.csv)")

if __name__ == "__main__":
    generate_noise_dataset()