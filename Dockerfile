# Dockerfile (النسخة النهائية والمحسنة)

# 1. صورة الأساس
FROM python:3.11-slim

# 2. متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright

# 3. تثبيت اعتماديات النظام (بما في ذلك gosu)
COPY packages.txt /tmp/
RUN apt-get update && \
    apt-get install -y --no-install-recommends $(cat /tmp/packages.txt) && \
    rm -rf /var/lib/apt/lists/*

# 4. إنشاء المستخدم ومجلد العمل
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# 5. تحديث متغير PATH
ENV PATH="/home/appuser/.local/bin:${PATH}"

# 6. نسخ الملفات وتثبيت المكتبات (سيتم ضبط الملكية عبر entrypoint)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY . .

# 7. تحديد نقطة الدخول
ENTRYPOINT ["/home/appuser/app/entrypoint.sh"]

# 8. تحديد المنفذ والأمر الافتراضي
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
