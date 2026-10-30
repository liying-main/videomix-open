@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo   厉影AI 混剪 开源版
echo   模型与算力来自 https://api.openapi.cn
echo ================================================
echo.

if "%VIDEOMIX_API_KEY%"=="" (
  echo [!] 还没有设置 VIDEOMIX_API_KEY
  echo     请到 https://api.openapi.cn 创建令牌后执行：
  echo     set VIDEOMIX_API_KEY=sk-你的key
  echo.
)

python -m videomix --web
pause
