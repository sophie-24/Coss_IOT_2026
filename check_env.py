import sys
import os

print("="*50)
print("🔍 파이썬 환경 디버깅 리포트")
print(f"현재 실행 중인 Python 경로: {sys.executable}")
print(f"Python 버전: {sys.version}")
print("="*50)

try:
    import tensorflow as tf
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input
    import tensorflow_hub as hub
    import librosa

    print("\n✅ [SUCCESS] 모든 필수 라이브러리 임포트 성공!")
    print(f"TensorFlow 버전: {tf.__version__}")
    print(f"TF-Hub 버전: {hub.__version__}")
    print(f"Librosa 버전: {librosa.__version__}")

except ImportError as e:
    print("\n❌ [FAILED] 임포트 에러 발생!")
    print(f"에러 메시지: {e}")
    print("\n💡 해결 팁:")
    print(f"터미널에 다음 명령어를 입력한 뒤 다시 실행해 보세요:")
    print(f"'{sys.executable} -m pip install tensorflow tensorflow-hub librosa'")

print("="*50)