@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo   WeChat AI Publisher - 添加到开机启动
echo ==========================================
echo.

REM 获取程序路径
set "EXE_PATH=%~dp0dist\WeChatAI_Publisher_Portable\WeChatAI_Publisher.exe"

REM 检查程序是否存在
if not exist "%EXE_PATH%" (
    echo 错误: 未找到程序文件
    echo 请先运行 build.py 打包程序
    pause
    exit /b 1
)

REM 设置启动文件夹路径
set "STARTUP_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

REM 创建快捷方式（使用 PowerShell）
echo 正在创建快捷方式...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTUP_PATH%\WeChatAI_Publisher.lnk'); $Shortcut.TargetPath = '%EXE_PATH%'; $Shortcut.WorkingDirectory = '%~dp0dist\WeChatAI_Publisher_Portable'; $Shortcut.Save()"

if %ERRORLEVEL% == 0 (
    echo.
    echo ==========================================
    echo   设置成功！
    echo ==========================================
    echo.
    echo 程序路径: %EXE_PATH%
    echo 快捷方式: %STARTUP_PATH%\WeChatAI_Publisher.lnk
    echo.
    echo 下次开机时将自动启动程序
    echo 如需取消，删除上述快捷方式即可
    echo ==========================================
) else (
    echo.
    echo 设置失败，请尝试手动运行 setup_startup.py
)

pause
