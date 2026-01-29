# build_dataset.py
import os
import json
import pandas as pd
import numpy as np
import logging
from ai_model import preprocess_audio_data, DEFAULT_SAMPLING_RATE, MFCC_COUNT

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_dataset_from_real_data(
    labels_file="labels.csv", 
    data_dir="collected_dataset", 
    output_file="real_noise_data.csv"
):
    """
    Builds a training-ready dataset from raw collected JSON files and a manual labels file.

    1. Reads a CSV file with 'filename' and 'label' columns.
    2. Opens each corresponding JSON file from the data directory.
    3. Extracts 'sound_raw' and 'vibration' data.
    4. Processes 'sound_raw' into MFCC features using the function from ai_model.py.
    5. Saves the processed features and labels into a new CSV file ready for training.
    """
    if not os.path.exists(labels_file):
        logging.error(f"'{labels_file}' not found. Please create it first with 'filename' and 'label' columns.")
        return

    if not os.path.exists(data_dir):
        logging.error(f"'{data_dir}' directory not found. No data to process.")
        return

    try:
        labels_df = pd.read_csv(labels_file)
    except Exception as e:
        logging.error(f"Error reading '{labels_file}': {e}")
        return

    processed_dataset = []
    logging.info(f"Found {len(labels_df)} entries in '{labels_file}'. Starting processing...")

    for index, row in labels_df.iterrows():
        filename = row['filename']
        label = row['label']
        json_path = os.path.join(data_dir, filename)

        if not os.path.exists(json_path):
            logging.warning(f"File '{filename}' listed in labels but not found in '{data_dir}'. Skipping.")
            continue

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract data from the JSON structure
            sound_raw = data['payload']['sound_raw']
            vibration_z = data['payload']['vibration']['z']
            sampling_rate = int(data['meta']['sampling_rate'].replace('Hz', ''))

            # Convert raw sound to numpy array of floats
            audio_np = np.array(sound_raw, dtype=np.float32)

            # Process raw audio to get MFCC features (the "sound_sample")
            # This ensures the features are identical to what the live model would see
            sound_features = preprocess_audio_data(audio_np, sr=sampling_rate, n_mfcc=MFCC_COUNT)

            processed_dataset.append({
                "vibration_sample": vibration_z, # Use the raw vibration data
                "sound_sample": sound_features.tolist(), # These are the MFCCs
                "label": label
            })
            logging.info(f"Processed '{filename}' for label '{label}'.")

        except Exception as e:
            logging.error(f"Error processing file '{filename}': {e}")

    if not processed_dataset:
        logging.warning("No data was processed. The output file will not be created.")
        return

    # Create the final DataFrame and save it
    output_df = pd.DataFrame(processed_dataset)
    output_df.to_csv(output_file, index=False)
    logging.info(f"✅ Successfully created '{output_file}' with {len(output_df)} processed samples.")

if __name__ == "__main__":
    build_dataset_from_real_data()
