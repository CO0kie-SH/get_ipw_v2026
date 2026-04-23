@chcp 936>nul
@title IP ²é¿´
@cd /d %~dp0
::set PYTHONIOENCODING=utf-8

@set path=D:\0Code2\py312;%path%
@set path=D:\job\py312\Scripts;D:\job\py312;%path%

::set fei_title="Îç·¹ÌáÐÑ£¡"
@set only_work=Workday

python main.py --user1 %*
