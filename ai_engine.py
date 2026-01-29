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
MAX_STEPS = 5
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
    
    # Return True if all models are already loaded
    if all([_model_v2, _class_names_v2, _yamnet_model]):
        return True

    try:
        logger.info("Loading AI model V2, class names, and YAMNet model...")
        _model_v2 = tf.keras.models.load_model(model_path)
        _class_names_v2 = np.load(class_names_path, allow_pickle=True)
        _yamnet_model = hub.load(YAMNET_MODEL_HANDLE)
        logger.info("✅ Successfully loaded all V2 model assets.")
        return True
    except Exception as e:
        logger.exception(f"❌ Critical error loading V2 model assets from {model_path} or {class_names_path}.")
        _model_v2, _class_names_v2, _yamnet_model = None, None, None # Ensure clean state on failure
        return False

def preprocess_audio_for_v2(audio_data: np.ndarray, sr: int) -> np.ndarray:
    """
    Preprocesses raw audio data for the V2 model by extracting YAMNet embeddings.
    The process:
    1. Resamples the audio to the required 16kHz for YAMNet.
    2. Extracts embeddings using YAMNet.
    3. Pads or slices the embeddings to a fixed sequence length (MAX_STEPS).
    4. Reshapes the data to match the model's input: (1, MAX_STEPS, 1024).
    """
    if _yamnet_model is None:
        logger.error("YAMNet model is not loaded. Cannot preprocess audio.")
        return None

    # 1. Resample audio if necessary
    if sr != YAMNET_SR:
        audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=YAMNET_SR)
    
    # 2. Get embeddings from YAMNet
    # The model returns: scores, embeddings, and spectrogram
    _, embeddings, _ = _yamnet_model(audio_data)
    
    # 3. Pad or slice the embeddings to the fixed sequence length
    num_embeddings = embeddings.shape[0]
    
    if num_embeddings > MAX_STEPS:
        # If more embeddings than needed, take the last MAX_STEPS
        processed_embeddings = embeddings[-MAX_STEPS:, :]
    else:
        # If fewer, pad with zeros at the beginning
        pad_width = MAX_STEPS - num_embeddings
        processed_embeddings = np.pad(embeddings, ((pad_width, 0), (0, 0)), mode='constant')

    # 4. Reshape for the model input: (1, time_steps, features)
    return processed_embeddings.reshape(1, MAX_STEPS, EMBEDDING_SIZE)


def predict_noise_v2(processed_audio: np.ndarray) -> Tuple[str, float]:
    """
    Performs inference using the loaded V2 model.
    """
    if _model_v2 is None or _class_names_v2 is None:
        logger.error("V2 model or class names not loaded. Cannot perform prediction.")
        return "ERROR", 0.0

    # Get model prediction
    prediction = _model_v2.predict(processed_audio)
    
    # Get the class with the highest probability
    predicted_class_index = np.argmax(prediction[0])
    predicted_class_name = _class_names_v2[predicted_class_index]
    predicted_probability = float(np.max(prediction[0]))
    
    logger.info(f"V2 Model Prediction: '{predicted_class_name}' with {predicted_probability:.2f} confidence.")
    
    return predicted_class_name, predicted_probability
