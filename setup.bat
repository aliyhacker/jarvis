@echo off
chcp 65001 >nul
echo.
echo ============================================
echo        J.A.R.V.I.S  Windows Kurulum
echo ============================================
echo.

REM Python kontrolu
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi. python.org adresinden Python 3.10+ yukle
    echo        ve kurulumda "Add Python to PATH" secenegini isaretle.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i

REM Virtual environment
if not exist "venv" (
    echo [*] Sanal ortam olusturuluyor...
    python -m venv venv
)
call venv\Scripts\activate.bat

REM API anahtari dosyasi
if not exist "config\api_keys.json" (
    copy "config\api_keys.example.json" "config\api_keys.json" >nul
    echo [*] config\api_keys.json olusturuldu - Gemini API anahtarini buraya gir
    echo     ^(veya program acilinca ekrandaki ayarlardan girebilirsin^)
)

echo [*] Paketler yukleniyor ^(opencv ilk seferde biraz surebilir^)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

REM Fontlari Windows font dizinine kur (yonetici gerekebilir)
if exist "Fonts" (
    echo [*] Grift fontlari kuruluyor...
    for %%f in (Fonts\*.ttf) do (
        copy "%%f" "%WINDIR%\Fonts\" >nul 2>&1
    )
    echo [OK] Fontlar kuruldu ^(basarisiz olursa Fonts klasorunden sag tik^> Yukle^)
)

echo.
echo ============================================
echo            Kurulum Tamamlandi!
echo ============================================
echo.
echo Baslatmak icin: BASLAT.bat dosyasina cift tikla
echo                 ^(veya: venv\Scripts\activate.bat ^&^& python main.py^)
echo.
set /p choice="Simdi baslatilsin mi? (e/h): "
if /i "%choice%"=="e" python main.py
