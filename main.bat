@chcp 65001>nul
@title IP 查看 v26.5.23A
@cd /d %~dp0
@set PYTHONIOENCODING=utf-8

@set path=D:\0Code2\py312;%path%
@set path=D:\job\py312\Scripts;D:\job\py312;%path%

:: 版本信息：26.5.23A (2026-05-23)

set fei_title="播报标题BAT"
set only_work=Workday

python main.py %*
