#!/bin/bash
# يضمن أن السكربت سيتوقف إذا فشل أي أمر
set -e

# هذا الجزء من السكربت يعمل كـ root
echo "🔧 Fixing permissions for app and cache directories..."
# نقوم بإنشاء مجلد الكاش إذا لم يكن موجودًا لضمان وجوده قبل تغيير الملكية
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
chown -R appuser:appuser /home/appuser/app "$PLAYWRIGHT_BROWSERS_PATH"

echo "✅ Permissions fixed. Switching to user 'appuser' to run the command..."
echo "------------------------------------------------------------"

# نستخدم gosu للانتقال إلى المستخدم appuser
# ثم نستخدم bash -c لتنفيذ سلسلة من الأوامر
# "$@" في النهاية تمرر الأمر الأصلي من 'docker run' إلى السكربت
exec gosu appuser bash -c '
  set -e
  echo "--> Now running as user: $(whoami)"
  
  echo "--> Checking and installing Playwright browser if needed..."
  python -m playwright install chromium
  
  echo "--> Playwright setup complete."
  echo "------------------------------------------------------------"
  
  echo "🚀 Executing main command: $@"
  exec "$@"
' -- "$@"
