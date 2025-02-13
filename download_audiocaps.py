# JUST HELPER METHODS IN THIS CELL 

import subprocess
import os
from pathlib import Path
from multiprocessing import Pool
from tqdm.auto import tqdm
import torchaudio

import pandas as pd


def download_clip(
    video_identifier,
    output_filename,
    num_attempts=5,
    url_base='https://www.youtube.com/watch?v='
):
    status = False

    command = f"""
        yt-dlp --quiet --no-warnings -x --audio-format wav -f bestaudio -o "{output_filename}" {url_base}{video_identifier}
    """.strip()

    attempts = 0
    while True:
        try:
            output = subprocess.check_output(command, shell=True,
                                                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as err:
            attempts += 1
            if attempts == num_attempts:
                return status, err.output
        else:
            break

    # Check if the video was successfully saved.
    status = os.path.exists(output_filename)
    return status, 'Downloaded'


def process(example):

    outfile_path = str(data_dir + '/' + f"{example['youtube_id']}_tmp.wav")
    processed_outfile_path = str(data_dir + '/' + f"{example['youtube_id']}.wav")

    try:
        download_clip(
            example['youtube_id'],
            outfile_path,
        )

        if not os.path.exists(outfile_path):
            raise Exception(f"file was not downloaded {example['youtube_id']}")

        start_time = example['start_time']
        end_time = start_time + 9

        waveform, sample_rate = torchaudio.load(outfile_path)
        waveform = waveform.mean(dim=0, keepdim=True)

        start_sample_rate = sample_rate * start_time
        end_sample_rate = sample_rate * end_time
        if start_sample_rate > waveform.shape[1] or end_sample_rate > waveform.shape[1]:
            raise Exception(f"bad file ranges (start {start_time}, end {end_time}): while length only {waveform.shape[1] / sample_rate}")

        waveform = waveform[0:, start_sample_rate:end_sample_rate]

        expected_sample_rate = 16000
        if sample_rate != expected_sample_rate:
            waveform = torchaudio.functional.resample(waveform, orig_freq=sample_rate, new_freq=expected_sample_rate)
            sample_rate = expected_sample_rate

        torchaudio.save(processed_outfile_path, waveform, sample_rate)

    except Exception as e:
        print("error processing sample ", example['youtube_id'], e)

    try:
        os.remove(outfile_path)
    except Exception as ee:
        pass


    return example

def process_dataset_idx(i):
    example = dataset.iloc[i]
    return process(example)

csv_path = "dataset/train.csv"
dataset = pd.read_csv(csv_path)

data_dir = '../data/audiocaps_train'

with Pool(processes=4) as pool:
    result = list(tqdm(pool.imap(process_dataset_idx, range(len(dataset))), total=len(dataset), desc='prepare audio files'))
