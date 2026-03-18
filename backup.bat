@echo off
echo 🔄 Creating backup...
if not exist "d:\PG\backups" mkdir "d:\PG\backups"
set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
set TIMESTAMP=%TIMESTAMP: =0%
copy "d:\PG\backend\arpg_database.db" "d:\PG\backups\arpg_db_%TIMESTAMP%.db"
echo ✅ Backup created!
pause