import logging
import os
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import librosa
from typing import Tuple

# --- Constants ---
# YAMNet model constants
YAMNET_MODEL_HANDLE = 'https://tfhub.dev/google/yamnet/1'
YAMNET_SR = 16000
YAMNET_MONO = True

# V2 model input specifications
MAX_STEPS = 20
EMBEDDING_SIZE = 1024

# --- Logging ---
logger = logging.getLogger(__name__)

# --- Global Cache ---
_model_v2 = None
_class_names_v2 = None
_yamnet_model = None

def load_ai_model_v2(
    model_path: str = "models/noise_classification_v2.keras",
    class_names_path: str = "models/classes_v2.npy"
) -> bool:
    """
    Loads and caches the V2 classification model, class names, and the YAMNet model.
    """
    global _model_v2, _class_names_v2, _yamnet_model
    
    if all([_model_v2 is not None, _class_names_v2 is not None, _yamnet_model is not None]):
        return True

    try:
        logger.info("Loading AI model V2, class names, and YAMNet model...")
        
        # Load custom trained V2 model
        if os.path.exists(model_path):
            _model_v2 = tf.keras.models.load_model(model_path)
        else:
            logger.error(f"Model file not found at {model_path}")
            return False
            
        # Load class names
        if os.path.exists(class_names_path):
            _class_names_v2 = np.load(class_names_path, allow_pickle=True)
        else:
            logger.error(f"Class names file not found at {class_names_path}")
            return False
            
        # Load YAMNet from TFHub
        _yamnet_model = hub.load(YAMNET_MODEL_HANDLE)
        
        logger.info("✅ Successfully loaded all V2 model assets.")
        return True
    except Exception as e:
        logger.exception(f"❌ Critical error loading V2 model assets: {e}")
        _model_v2, _class_names_v2, _yamnet_model = None, None, None
        return False
def preprocess_audio_for_v2(audio_data: np.ndarray, sr: int) -> np.ndarray:
    """
    Preprocesses audio data: Resample to 16kHz -> YAMNet -> Embeddings -> Pad/Crop
    Returns: (1, MAX_STEPS, 1024) tensor or None on failure.
    """
    if _yamnet_model is None:
        logger.error("YAMNet model is not loaded.")
        return None

    try:
        # 1. Resample to 16000 Hz if necessary
        if sr != YAMNET_SR:
            resampled_audio = librosa.resample(audio_data, orig_sr=sr, target_sr=YAMNET_SR)
        else:
            resampled_audio = audio_data

        # [핵심 수정] 2. YAMNet 모델은 무조건 1차원 데이터만 받습니다. 
        # 혹시 모를 차원을 완전히 펴서(flatten) 전달합니다.
        waveform = tf.convert_to_tensor(resampled_audio, dtype=tf.float32)
        waveform = tf.reshape(waveform, [-1]) # [None] 형태로 강제 변환

        # scores, embeddings, spectrogram = model(waveform)
        _, embeddings, _ = _yamnet_model(waveform)
        
        # embeddings shape: (N, 1024)
        embeddings_np = embeddings.numpy()
        
        # 3. Pad or Truncate to MAX_STEPS (5 steps)
        current_steps = embeddings_np.shape[0]
        
        if current_steps < MAX_STEPS:
            padding = np.zeros((MAX_STEPS - current_steps, EMBEDDING_SIZE))
            processed_embeddings = np.vstack([embeddings_np, padding]) if current_steps > 0 else padding
        else:
            processed_embeddings = embeddings_np[:MAX_STEPS, :]
            
        # 4. Add Batch Dimension: (1, 5, 1024)
        return np.expand_dims(processed_embeddings, axis=0)

    except Exception as e:
        # 이 로그가 찍혔던 이유를 잡았습니다!
        logger.error(f"Error in audio preprocessing: {e}")
        return None

def predict_noise_v2(audio_data: np.ndarray, sr: int, vibration_z: list) -> Tuple[str, float]:
    """
    Performs inference using the Multi-modal V2 model (Audio + Vibration).
    
    Args:
        audio_data: Raw audio samples (float32)
        sr: Sampling rate of audio
        vibration_z: List of Z-axis acceleration values
        
    Returns:
        (Predicted Class Name, Probability)
    """
    if _model_v2 is None:
        logger.error("V2 Model is not loaded.")
        return "Error", 0.0

    # 1. Process Audio
    audio_input = preprocess_audio_for_v2(audio_data, sr)
    if audio_input is None:
        return "Error", 0.0

    # 2. Process Vibration
    # Calculate statistical features: Mean, Std, Max, RMS
    try:
        vibe_np = np.array(vibration_z)
        
        if vibe_np.size == 0:
            # Handle empty vibration data gracefully (e.g., zeros)
            vibe_features = np.zeros((1, 4))
        else:
            mean_val = np.mean(vibe_np)
            std_val = np.std(vibe_np)
            max_val = np.max(vibe_np)
            rms_val = np.sqrt(np.mean(vibe_np**2))
            
            # Shape: (1, 4)
            vibe_features = np.array([[mean_val, std_val, max_val, rms_val]])
    except Exception as e:
        logger.error(f"Error processing vibration data: {e}")
        return "Error", 0.0

    # 3. Predict
    try:
        # Model expects a list of inputs: [audio_input, vibration_input]
        predictions = _model_v2.predict([audio_input, vibe_features], verbose=0)
        
        # predictions shape: (1, num_classes)
        predicted_index = np.argmax(predictions[0])
        predicted_prob = float(predictions[0][predicted_index])
        
        if _class_names_v2 is not None:
            result_label = _class_names_v2[predicted_index]
        else:
            result_label = f"Class {predicted_index}"
            
        return result_label, predicted_prob

    except Exception as e:
        logger.exception(f"Error during V2 inference: {e}")
        return "Error", 0.0
