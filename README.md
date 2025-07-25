<div align="center">
    <h1>🏦 حاسبة أذون الخزانة المصرية 🏦</h1>
  <p><strong>تطبيقك الأمثل لتحليل وحساب عوائد أذون الخزانة المصرية بدقة وسهولة.</strong></p>
  
  <p>
    <a href="https://treasury-bills-calc.streamlit.app/" target="_blank"><img src="https://img.shields.io/badge/Launch-App-FF4B4B?logo=streamlit" alt="Launch App"></a>
    <a href="https://github.com/Al-QaTari/Treasury-Bills-Calc/actions/workflows/quality_check.yml"><img src="https://github.com/Al-QaTari/Treasury-Bills-Calc/actions/workflows/quality_check.yml/badge.svg" alt="Code Quality Check"></a>
    <a href="https://github.com/Al-QaTari/Treasury-Bills-Calc/actions/workflows/scheduled_scrape.yml"><img src="https://img.shields.io/badge/Scheduled_Scrape-Passed-brightgreen?logo=github" alt="Scheduled Scrape"></a>
    <a href="https://streamlit.io" target="_blank"><img src="https://img.shields.io/badge/Made_with-Streamlit-FF4B4B?logo=streamlit" alt="Made with Streamlit"></a>
    <a href="https://www.python.org/" target="_blank"><img src="https://img.shields.io/badge/Python-3.11%2B-blue?logo=python" alt="Python Version"></a>
    <a href="https://github.com/Al-QaTari/Treasury-Bills-Calc/actions/workflows/virus-scan.yml"><img src="https://github.com/Al-QaTari/Treasury-Bills-Calc/actions/workflows/virus-scan.yml/badge.svg"></a>
  </p>
</div>

---

## 📖 جدول المحتويات
1. [عن المشروع](#-عن-المشروع)
2. [الميزات الرئيسية](#-الميزات-الرئيسية)
3. [التشغيل محلياً](#-التشغيل-محلياً)
4. [التشغيل باستخدام Docker](#-التشغيل-باستخدام-docker)
5. [هيكل المشروع](#-هيكل-المشروع)
6. [الترخيص](#-الترخيص-license)
7. [المساهمة](#-المساهمة)
8. [المؤلف](#المؤلف)

---

## 🎯 عن المشروع

تطبيق ويب تفاعلي ومفتوح المصدر، تم بناؤه باستخدام **Streamlit** لمساعدة المستثمرين في السوق المصري على اتخاذ قرارات استثمارية مدروسة. يقوم التطبيق بسحب أحدث بيانات عطاءات أذون الخزانة بشكل آلي من موقع البنك المركزي المصري ويحولها إلى أرقام ورؤى واضحة.

---

## ✨ الميزات الرئيسية

| الميزة | الوصف |
| :--- | :--- |
| **📊 جلب آلي للبيانات**  | سحب أحدث بيانات العطاءات مباشرة من موقع البنك المركزي المصري لضمان دقة الأرقام. |
| **🧮 حاسبة العائد الأساسية**  | حساب صافي الربح، الضرائب، ونسبة العائد الفعلية عند الشراء والاحتفاظ حتى الاستحقاق. |
| **⚖️ حاسبة البيع الثانوي**  | تحليل قرار البيع المبكر وحساب الربح أو الخسارة المحتملة بناءً على العائد السائد في السوق. |
| **🗄️ قاعدة بيانات تاريخية**  | حفظ البيانات المجلوبة في قاعدة بيانات SQLite لتتبع التغيرات في العوائد مع مرور الوقت. |
| **🗄️ قاعدة بيانات PostgreSQL**  | كقاعدة بيانات قوية موثوقة لضمان سلامة البيانات وإتاحتها للتحليل طويل الأمد PostgreSQLاستخدام. |
| **⚙️ أتمتة كاملة (CI/CD)**  | استخدام GitHub Actions لفحص جودة الكود، وتطبيق التنسيق، وتشغيل الاختبارات تلقائياً. |
| **💡 شرح مفصل**  | قسم للمساعدة يشرح المفاهيم المالية الأساسية وكيفية عمل الحاسبات. |

---

## 🚀 التشغيل محلياً

اتبع هذه الخطوات لتشغيل المشروع على جهازك.

#### 1️⃣ المتطلبات الأساسية
- Python 3.8 أو أحدث.
- متصفح Google Chrome.
- أداة `git`.

#### 2️⃣ تثبيت المشروع
```bash
# انسخ المستودع إلى جهازك
git clone https://github.com/Al-QaTari/Treasury-Bills-Calc.git

# ادخل إلى مجلد المشروع
cd Treasury-Bills-Calc

# ثبّت جميع المكتبات المطلوبة
pip install -r requirements.txt
```

#### 3️⃣ تحديث البيانات (خطوة هامة)
```bash
# شغّل سكربت تحديث البيانات لجلب أحدث العوائد
python update_data.py
```
> **ملاحظة:** قد تستغرق هذه العملية دقيقة أو اثنتين في المرة الأولى.

#### 4️⃣ تشغيل التطبيق
```bash
# شغّل تطبيق Streamlit
streamlit run app.py
```
سيفتح التطبيق تلقائيًا في متصفحك على `http://localhost:8501`.

---

## 🐳 التشغيل باستخدام Docker

يمكنك تشغيل التطبيق بسهولة باستخدام Docker لبيئة معزولة ومتسقة.

#### 1️⃣ المتطلبات الأساسية
- تثبيت Docker على جهازك. يمكنك تنزيله من [الموقع الرسمي لـ Docker](https://www.docker.com/get-started).

#### 2️⃣ بناء صورة Docker

من داخل مجلد المشروع، قم ببناء صورة Docker:

```bash
docker build -t treasury-app .
```

#### 3️⃣ تشغيل حاوية Docker

بعد بناء الصورة، يمكنك تشغيل التطبيق في حاوية Docker:

```bash
docker run -p 8501:8501 -it --name treasury-app-container --env-file .env -v playwright-cache:/home/appuser/.cache/ms-playwright treasury-app
```

سيصبح التطبيق متاحًا في متصفحك على `http://localhost:8501`.

#### 4️⃣ تحديث البيانات داخل حاوية Docker

إذا كنت ترغب في تحديث البيانات يدويًا داخل الحاوية بعد تشغيلها، يمكنك تنفيذ الأمر التالي:

```bash
docker run -it --rm --env-file .env -v playwright-cache:/home/appuser/.cache/ms-playwright -v ${pwd}/data:/home/appuser/app/data treasury-app python update_data.py --force-refresh
```

#### **ملاحظة:** يفضل عند كل ايقاف للمشروع استخدام الامر التالي لضمان ان التعديلات لا تتداخل 

```bash
docker stop treasury-app-container; docker rm treasury-app-container
```

---

## 📂 هيكل المشروع
```
Treasury-Bills-Calc/
│
├── .github/
│   └── workflows/
│       ├── quality_check.yml------------# فحص جودة وتنسيق الكود تلقائيًا.
│       ├── scheduled_scrape.yml-------- # تحديث البيانات بشكل مجدول (يوميًا).
│       └── virus-scan.yml---------------# فحص أمان الكود ضد الفيروسات والبرمجيات الخبيثة.
│
├── css/
│   └── style.css------------------------# تنسيقات CSS لتجميل واجهة المستخدم.
│
├── tests/
│   ├── __init__.py----------------------# ملف تهيئة لجعل المجلد حزمة قابلة للاختبار.
│   ├── test_calculations.py-------------# اختبارات دوال العمليات الحسابية.
│   ├── test_cbe_scraper.py--------------# اختبارات تحليل بيانات البنك المركزي.
│   ├── test_db_manager.py---------------# اختبارات مدير قاعدة البيانات SQLite.
│   ├── test_postgre_integration.py------# اختبارات تكامل مع PostgreSQL.
│   ├── test_ui.py-----------------------# اختبارات واجهة المستخدم باستخدام Playwright.
│   └── test_integration.py--------------# اختبار تكامل المكونات مع بعضها
│
│
├── treasury_core/-----------------------# الطبقة المنفذة للواجهات (ports/models)
│    ├── __init__.py---------------------# تهيئة الحزمة.
│    ├── calculations.py-----------------# دوال الحسابات المالية (العائد، الضرائب، إلخ)              
│    ├── models.py-----------------------# نماذج البيانات.
│    └── ports.py------------------------# واجهات مجردة للتخزين والاسترجاع.
│
├── app.py-------------------------------# الملف الرئيسي لتطبيق Streamlit.
├── calculations.py----------------------# دوال لحساب العائدات، الضرائب، وصافي الربح.
├── cbe_scraper.py-----------------------# جلب وتحليل بيانات أذون الخزانة من موقع البنك.
├── postgres_manager.py------------------# مدير قاعدة بيانات PostgreSQL.
├── constants.py-------------------------# يحتوي على أسماء الأعمدة والثوابت العامة.
├── update_data.py-----------------------# سكربت لجلب البيانات وتحديثها يدويًا.
├── utils.py-----------------------------# دوال مساعدة عامة.
│
├── entrypoint.sh------------------------# سكربت الدخول المخصص لـ Docker.
├── setup.sh-----------------------------# سكربت إعداد بيئة التشغيل (مثل تثبيت Playwright).
├── pytest.ini---------------------------# إعدادات Pytest الافتراضية.
│
├── .gitignore---------------------------# تجاهل ملفات مثل البيئة الافتراضية والمخرجات المؤقتة.
├── LICENSE.txt--------------------------# ملف الترخيص (MIT License).
├── README.md----------------------------# ملف التوثيق الأساسي للمشروع.
├── packages.txt-------------------------# متطلبات النظام لتشغيل المشروع (مناسب لـ Streamlit Cloud).
└── requirements.txt---------------------# مكتبات بايثون المطلوبة لتشغيل التطبيق.

```

---

## 📜 الترخيص (License)

هذا المشروع مرخص بموجب **ترخيص MIT**، وهو أحد أكثر تراخيص البرمجيات الحرة تساهلاً. هذا يمنحك حرية كبيرة في استخدام وتطوير البرنامج.

#### ✓ لك مطلق الحرية في:
- **الاستخدام التجاري**: يمكنك استخدام هذا البرنامج في أي مشروع تجاري وتحقيق الربح منه.
- **التعديل والتطوير**: يمكنك تعديل الكود المصدري ليناسب احتياجاتك الخاصة.
- **التوزيع**: يمكنك إعادة توزيع البرنامج بنسخته الأصلية أو بعد تعديله.

#### ⚠️ الشرط الوحيد:
- **الإبقاء على الإشعار**: يجب عليك الإبقاء على إشعار حقوق النشر والترخيص الأصلي مضمنًا في جميع نسخ البرنامج.

#### 🚫 إخلاء المسؤولية:
- **بدون ضمان**: البرنامج مقدم "كما هو" دون أي ضمان من أي نوع، سواء كان صريحًا أو ضمنيًا.
- **بدون مسؤولية**: لا يتحمل المؤلف أي مسؤولية عن أي أضرار قد تنشأ عن استخدام البرنامج.

<p align="center">
  <a href="https://github.com/Al-QaTari/Treasury-Bills-Calc/blob/main/LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
  <br>
  <small>للاطلاع على النص الكامل للترخيص، اضغط على الشارة أعلاه</small>
</p>

---

## 🤝 المساهمة

المساهمات هي ما تجعل مجتمع المصادر المفتوحة مكانًا رائعًا للتعلم والإلهام والإبداع. أي مساهمات تقدمها ستكون موضع **تقدير كبير**.

1.  قم بعمل Fork للمشروع.
2.  أنشئ فرعًا جديدًا للميزة الخاصة بك (`git checkout -b feature/AmazingFeature`).
3.  قم بعمل Commit لتغييراتك (`git commit -m 'Add some AmazingFeature'`).
4.  ارفع تغييراتك إلى الفرع (`git push origin feature/AmazingFeature`).
5.  افتح Pull Request.

---

<h2 align="center">المؤلف</h2>
<p align="center"><strong>Mohamed AL-QaTri</strong> - <a href="https://github.com/Al-QaTari">GitHub</a></p>


---

<h3 align="center">⚠️ إخلاء مسؤولية</h3>
<p align="center">
هذا التطبيق هو أداة إرشادية فقط. للحصول على أرقام نهائية ودقيقة، يرجى الرجوع دائمًا إلى البنك أو المؤسسة المالية التي تتعامل معها.
</p>
