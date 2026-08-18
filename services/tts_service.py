"""
TTS 语音合成服务 (Edge TTS)

使用 edge-tts 实现文字转语音，支持异步合成和播放。
"""
import asyncio
import tempfile
from pathlib import Path
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, QObject, pyqtSignal

from config import DEFAULT_VOICE, AUDIO_CACHE_DIR


class TTSService(QObject):
    """TTS 语音合成服务"""

    finished = pyqtSignal()
    playback_started = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._current_temp_file: str | None = None

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    async def speak(self, text: str, voice: str = DEFAULT_VOICE,
                    speed: int = 0) -> None:
        """将文本合成为语音并播放"""
        temp_path = await self._synthesize(text, voice, speed)
        self._play_file(temp_path)

    async def play_file(self, file_path: str) -> None:
        """播放指定的音频文件（用于自定义语音）"""
        self._play_file(file_path)

    async def synthesize_to_file(self, text: str, output_path: str,
                                  voice: str = DEFAULT_VOICE, speed: int = 0) -> str:
        """将文本合成为音频文件"""
        import edge_tts
        rate = f"+{speed}%" if speed >= 0 else f"{speed}%"
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
        return output_path

    def stop(self):
        """停止播放"""
        self._player.stop()
        self._cleanup_temp()

    def set_volume(self, volume: int):
        """设置音量 (0~100)"""
        self._audio_output.setVolume(volume / 100.0)

    async def _synthesize(self, text: str, voice: str, speed: int) -> str:
        """合成语音到临时文件"""
        temp_file = tempfile.NamedTemporaryFile(
            suffix=".mp3", dir=AUDIO_CACHE_DIR, delete=False
        )
        output_path = temp_file.name
        temp_file.close()

        await self.synthesize_to_file(text, output_path, voice, speed)
        self._current_temp_file = output_path
        return output_path

    def _play_file(self, file_path: str):
        """播放音频文件"""
        url = QUrl.fromLocalFile(file_path)
        self._player.setSource(url)
        self._player.play()
        self.playback_started.emit()

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._cleanup_temp()
            self.finished.emit()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._cleanup_temp()
            self.error.emit("音频文件无效")

    def _cleanup_temp(self):
        if self._current_temp_file:
            try:
                Path(self._current_temp_file).unlink(missing_ok=True)
            except Exception:
                pass
            self._current_temp_file = None
