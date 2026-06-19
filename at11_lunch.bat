@chcp 65001>nul
@title IP 查看 v26.6.19F
@cd /d %~dp0
@set PYTHONIOENCODING=utf-8

@set path=D:\0Code2\py312;D:\0Code2\Py310avatr\Scripts;%path%
@set path=D:\job\py312\Scripts;D:\job\py312;%path%

:: 版本信息：26.6.19F (2026-06-19)
:: 仅工作日发送 user1 标签机器人

::set fei_title="飞书提醒"
@set only_work=Workday

python main.py --user1 %*
