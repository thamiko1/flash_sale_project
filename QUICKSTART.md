## 快速開始指南 (Quick Start)

### 1. 第一次啟動專案

在專案根目錄執行：
python3 -m pip install -r requirements.txt

# 建立資料表與測試資料
python3 manage.py migrate
python3 manage.py create_test_data

# （可選）建立後台管理帳號
python3 manage.py createsuperuser

### 2. 啟動伺服器
python3 manage.py runserver

伺服器啟動後，可在 `http://localhost:8000` 使用 API。