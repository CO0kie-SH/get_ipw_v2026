@chcp 65001>nul
@title IP 变化播报 v26.6.19F
@cd /d %~dp0
@set PYTHONIOENCODING=utf-8

@set path=D:\0Code2\py312;D:\0Code2\Py310avatr\Scripts;%path%
@set path=D:\job\py312\Scripts;D:\job\py312;%path%

:: version 26.6.19F (2026-06-19)
:: diff mode: skip broadcast when 4-line result matches last round (still logged).
:: Schedule every 3 min; keep diff_window slightly larger than the interval.

set fei_title="IP变化播报"

:: test scaffold: loop calling :check until count reaches 99
set /a count=0

:loop
call :check
if %count% lss 99 goto loop

echo loop end, count=%count%
pause
goto :eof

:: check function: echo + increment counter
:check
@echo ——检查%count%——
@set /a count+=1
python main.py --diff --diff_window 4 %*
@choice /C yn /T 180 /D y >nul

@goto :eof
:end0
