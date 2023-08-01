#!/usr/bin/env python3
#######################################
#chatGPT-voice-output--20230801       #
#将chatGP回复用语音输出By一个小兵         #
#该版用Edge-tts+mpv播放器               #  
#一个小兵 E-mail:shawokou123@gmail.com #
######################################

import asyncio
import io
import os
import tempfile
import shutil
import edge_tts
import subprocess 
import pydub
from pydub import AudioSegment

class TextToSpeech:
    def __init__(self, config):
        self.config = config
        self.hostname = "localhost"  # Replace with your hostname
        self.port = 8000  # Replace with your port number
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = config

    async def play_audio(self, audio_path):
        # 使用mpv播放语音文件
        try:
            subprocess.run(["mpv","--no-terminal" , "--speed=1.5", audio_path])
        except FileNotFoundError:
            print("Error: mpv command not found. Make sure mpv is installed and in the system PATH.")

    async def text2mp3(self, text, tts_lang):
        communicate = edge_tts.Communicate(text, tts_lang)
        duration = 0
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                duration = (chunk["offset"] + chunk["duration"]) / 1e7
        if duration == 0:
            raise RuntimeError(f"Failed to get tts from edge with voice={tts_lang}")
        audio_data.seek(0)
        return audio_data, duration

    async def generate_text_stream(self, file_path, max_paragraph_length=200):
        # This is a generator function that reads text from a local file and yields it as a stream
        with open(file_path, "r", encoding="utf-8") as file:
            current_paragraph = ""
            for line in file:
                line = line.strip()
                if line:
                    if len(current_paragraph) + len(line) + 1 > max_paragraph_length:
                        yield current_paragraph.strip()
                        current_paragraph = line + " "
                    else:
                        current_paragraph += line + " "
            if current_paragraph:
                yield current_paragraph.strip()

    async def save_audio_to_local(self, audio_data, output_path):
        with open(output_path, "wb") as f:
            shutil.copyfileobj(audio_data, f)

    async def get_and_save_audio(self, file_path, tts_lang, output_path):
        async def run_tts(text_stream, tts_lang, queue):
            counter = 1
            audio_files = []  # 用于存储所有录音文件名
            async for text in text_stream:
                try:
                    audio_data, duration = await self.text2mp3(text, tts_lang)
                except Exception as e:
                    print(f"Failed to generate TTS: {e}")
                    continue
                filename = f"{output_path[:-4]}_{counter}.mp3"
                counter += 1
                #print(f"一个小兵正在为你掉用Edge-tts来转换语音")
                await self.save_audio_to_local(audio_data, filename)
                audio_files.append(filename)  # 记录录音文件名
        

                #调用mpv播放生成的.mp3文件
                await self.play_audio(filename)
                #删除已朗读的.mp3文件
                #os.remove(filename)

            # 合并所有录音文件成一个output.mp3
            combined_audio = AudioSegment.empty()
            for audio_file in audio_files:
                audio_segment = AudioSegment.from_file(audio_file)
                combined_audio += audio_segment

            # 保存合并后的output.mp3
            combined_audio.export(output_path, format="mp3")

        queue = asyncio.Queue()
        task = asyncio.create_task(run_tts(self.generate_text_stream(file_path), tts_lang, queue))
        task.add_done_callback(lambda _: queue.put_nowait(None))
        await queue.get()
if __name__ == "__main__":
    # Example configuration
    config = {
        "localhost": True,  # Save audio to local computer instead of uploading to a server
        "tts_lang": "zh-CN-XiaoxiaoNeural"  # Replace with your desired TTS language code
    }

    # File paths for input text and output audio
    input_text_file = "cui_huifu.txt"
    output_audio_file = "output.mp3"

    # Create an instance of TextToSpeech and run the TTS process
    tts = TextToSpeech(config)
    asyncio.run(tts.get_and_save_audio(input_text_file, config["tts_lang"], output_audio_file))