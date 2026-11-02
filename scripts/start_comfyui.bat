@echo off
chcp 65001 >nul
cd /d D:\ComfyUI
call venv\Scripts\activate.bat
echo ============================================
echo  ComfyUI 启动中 ... 稍等出现 "To see the GUI go to:"
echo  然后在浏览器打开 http://127.0.0.1:8188
echo ============================================
python main.py --listen 0.0.0.0 --port 8188
pause
