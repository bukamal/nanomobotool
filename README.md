# Nano Mobi Tool

تطبيق أندرويد لصيانة أجهزة الموبايل، مبني بـ **Python + Flet** مع **pyjnius** كجسر إلى واجهات أندرويد الأصلية (`UsbManager`).

الموقع: `/root/nanomobotool/` — مستقل تماماً، بنفس تصميم وبنية مشروع `nano` المجاور.

بدأ المشروع داخل `/root/nano/nano mobi tool/` ثم نُقل إلى هنا لحل مشكلتين: المسافة في اسم المجلد (تُربك أدوات بناء Flutter)، وكونه داخل مستودع git الخاص بـ `nano` فيظهر كملفات غير متتبَّعة فيه.

---

## تصحيح مهم

كنت قد قلت سابقاً إن Flet لا يسمح بالتحكم في `AndroidManifest.xml`. **هذا خطأ**، وقد صحّحته بعد قراءة `pyproject.toml` في مشروع `nano`. Flet يدعم فعلاً:

| الإعداد | الفائدة هنا |
|---|---|
| `[tool.flet.android.feature]` | إعلان `android.hardware.usb.host` كمتطلب فعلي |
| `[tool.flet.android.manifest_application]` | ضبط خصائص `<application>` (مثل `allowBackup`) |
| `[tool.flet.android.permission]` | إعلان الصلاحيات |
| `[tool.flet.android] dependencies` | **إضافة `pyjnius`** — سبب قدرة Python على الوصول لـ USB |
| `[tool.flet.dev_packages]` + `extensions/` | إضافة Plugin أندرويد أصلي (Kotlin/Flutter) عند الحاجة |

القيد الوحيد الباقي فعلاً هو `<intent-filter>` (issue #6560 مفتوح) — أي لا "فتح تلقائي عند وصل الجهاز". الحل الحالي: فحص داخل التطبيق + طلب صلاحية وقت التشغيل. وإن أردت لاحقاً الفتح التلقائي، فالطريق هو extension أندرويد أصلي تحت `extensions/` بأسلوب `flet_native_files` في مشروع `nano`.

---

## البنية

```
pyproject.toml                    إعدادات Flet + pyjnius + usb.host feature + ruff/pytest
build_mobi_tool_apk.sh            بناء APK ونقله إلى dist/
src/
  main.py                         نقطة الدخول (رقيقة)
  mobi_tool/
    core/                         طبقة نقية — بلا Flet إطلاقاً
      device_db.py                جداول VID/PID -> الوضع والبروتوكول
      usb_bridge.py               UsbManager / UsbDeviceConnection عبر pyjnius
      mock_devices.py             بيانات تطوير لوضع سطح المكتب
    protocols/
      base.py                     عقد الـ Plugin + ProtocolRegistry
    services/
      device_service.py           تنسيق الفحص + ScanResult (بلا Flet)
    components/
      theme.py                    لوحة الألوان
      device_card.py              كرت الجهاز + شارة الوضع
    views/
      devices_view.py             الشاشة: تدمج المكونات وتدير الصفحة
tests/
  unit/                           منطق الكشف، السجل، خدمة الفحص
  integration/                    بناء شجرة Flet الحقيقية بلا خادم
  contract/                       عقود التغليف والطبقات (تحمي بناء أندرويد)
tools/
  device_detection_smoke_test.py  فحص مستقل بلا pytest ولا جهاز
```

### فصل الطبقات (مُفروض باختبار)

`core/` و`services/` و`protocols/` **ممنوعة** من استيراد Flet، و`tests/contract` يفرض هذا عبر تحليل AST — لا بحث نصي، حتى لا تُحسب كلمة "Flet" في تعليق كتبعية. الفائدة: كل منطق الكشف قابل للاختبار على أي جهاز بلا واجهة.

### إضافة دعم جهاز جديد

موضع واحد فقط: صف جديد في `device_db.USB_MODES` يربط `(VID, PID)` بوضع وبروتوكول. ثم — إن أردت سلوكاً — تنفيذ `DeviceProtocol` في `protocols/` وتسجيله في `ProtocolRegistry`.

---

## التشغيل

```bash
# سطح المكتب (بيانات تجريبية — لا USB)
cd src && python3 main.py

# الفحص المستقل (بلا pytest)
python3 tools/device_detection_smoke_test.py

# الاختبارات
uv sync --extra dev
uv run pytest
```

على سطح المكتب يعرض التطبيق 4 أجهزة تجريبية (Qualcomm EDL · MediaTek BROM · Fastboot · ADB).

### بناء APK

```bash
./build_mobi_tool_apk.sh
```

---

## حالة التحقق

- **39/39 اختباراً تنجح** في unit / integration / contract.
- سكربت الفحص المستقل: **8/8**.
- التطبيق **يُقلع فعلياً** بلا انهيار (فحص تشغيل 15 ثانية).
- اختبارات العقد أمسكت خطأً حقيقياً: سقوط `pyjnius` من إعدادات أندرويد عند إعادة كتابة `pyproject.toml`.

### ما لم يُتحقَّق منه

**طبقة USB نفسها غير مختبرة على جهاز حقيقي** — لا يوجد أندرويد في بيئة التطوير. الترتيب الموصى به للفحص على الجهاز:

1. **Context** — إن ظهر `No Android Context available`، فعّل مسار `MAIN_ACTIVITY_HOST_CLASS_NAME` في `usb_bridge._get_context()`.
2. **الاستيضاح** — هل يعيد `list_devices()` الجهاز الموصول مع الواجهات والـ endpoints؟
3. **الصلاحية** — هل يظهر الحوار وينجح الاستطلاع بعده؟
4. **`byte[]`** — `_new_byte_array` / `_read_byte_array` هي أكثر نقطة احتمالاً لاختلاف سلوك pyjnius. اختبرها أولاً.
5. **`claimInterface`** — الواجهات الماسوكة بتعريف kernel تحتاج `force=True`، وهذا يحتاج root غالباً.
6. **اختبار شامل بسيط** — `read_device_descriptor()` يقرأ 18 بايت عبر Control Transfer.
7. **الطاقة** — إن فشل إقلاع جهاز أثناء التفليش، استخدم USB hub مُغذّى عبر كابل OTG Y.

---

## مخاطر يجب معرفتها

1. **لا مستودع git بعد.** المشروع الآن مستقل تحت `/root/nanomobotool`، لكنه ليس تحت إدارة إصدارات. `git init` خطوة مستحسنة قبل أي عمل جاد.
2. **اختلاف نسخة Flet**: هذا المشروع على `flet>=0.85.2` (واجهة `ft.Padding` / `ft.Border` / `ft.Alignment`)، بينما `nano` مثبَّت على `flet==0.28.3` (واجهة `ft.padding` القديمة). المشروعان لا يمكن أن يتشاركا نفس البيئة الافتراضية بهذه الحالة. اختبارات `tests/integration` تكشف أي انحراف عند الترقية.
3. **لا جهاز أندرويد موصول** — طبقة USB نفسها لم تُختبر بعد (انظر «ما لم يُتحقَّق منه»).

---

## خارطة الطريق

| المرحلة | المحتوى | حاجز؟ |
|---|---|---|
| 1 ✅ | الكشف + الواجهة + سجل البروتوكولات | لا |
| 2 | ADB (shell, backup, scrcpy server) | لا |
| 3 | Fastboot (flash / unlock / getvar) | لا |
| 4 | Qualcomm EDL (Sahara + Firehose) + مدير أصول بتحقّق SHA-256 | يحتاج Firehose موقّعاً لكل SoC |
| 5 | Samsung Odin/Loke | لا |
| 6 | MediaTek BROM — محلياً بالكامل (توقيت حسّاس) | يحتاج DA موقّعاً على الشرائح الحديثة (DAA/SLA) |
| 7 | Remote Technician + نظام الورش (SaaS) | لا |

---

## حدود

- **تعديل الـ IMEI** غير قانوني في معظم الدول، ويسهّل بيع أجهزة محظورة.
- **تجاوز FRP / قفل التنشيط** موجود لمنع استخدام جهاز مسروق أُعيد ضبطه.

لن يُكتب أي منهما هنا. السيناريو الشرعي القريب — استعادة قسم NV/modem **من نسخة احتياطية للجهاز نفسه** بعد تفليش فاشل — يُبنى كجزء طبيعي من محرّك التفليش في المرحلة 4، لا كميزة منفصلة. التوزيع سيكون APK جانبياً / Enterprise.
