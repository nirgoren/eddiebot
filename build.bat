rmdir /s /q "./build"
rmdir /s /q "./dist"
del "./eddiebot.spec"
pyinstaller src/eddiebot.py
copy ViGEmBusSetup_x64.msi dist\eddiebot\ViGEmBusSetup_x64.msi
copy src\ViGEmClient.dll dist\eddiebot\ViGEmClient.dll
copy C:\dev\eddiebot\vcontroller\x64\Release\vcontroller.dll dist\eddiebot\vcontroller.dll
copy src\recordings.txt dist\eddiebot\recordings.txt
copy README.md dist\eddiebot\readme.txt
copy src\config.json dist\eddiebot\config.json
PAUSE