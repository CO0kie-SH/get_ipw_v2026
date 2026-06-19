@chcp 65001>nul
@title IP 变化播报 v26.6.19D
@cd /d %~dp0
@set PYTHONIOENCODING=utf-8

@set path=D:\0Code2\py312;%path%
@set path=D:\job\py312\Scripts;D:\job\py312;%path%

:: version 26.6.19D (2026-06-19)
:: diff mode: skip broadcast when 4-line result matches last round (still logged).
:: Schedule every 3 min; keep diff_window slightly larger than the interval.

set fei_title="IP变化播报"

python main.py --diff --diff_window 4 %*
