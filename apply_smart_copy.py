import os, re, ast

# 1. certificates.py
p = 'app/bot/handlers/student/certificates.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('f\"🔹 Sertifikat ID: {cert_num}\\n\"', 'f\"🔹 Sertifikat ID: <code>{cert_num}</code>\\n\"')
src = src.replace('f\"📜 Seriya: {cert.certificate_number}\"', 'f\"📜 Seriya: <code>{cert.certificate_number}</code>\"')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated certificates.py')

# 2. results.py
p = 'app/bot/handlers/student/results.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('f\"🔑 Sertifikat raqami: {cert.certificate_number}\"', 'f\"🔑 Sertifikat raqami: <code>{cert.certificate_number}</code>\"')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated results.py')

# 3. test_creator.py
p = 'app/bot/handlers/admin/test_creator.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('f\"🔑 Test kodi: {test.code}\\n\"', 'f\"🔑 Test kodi: <code>{test.code}</code>\\n\"')
src = src.replace('f\"🔑 Test kodi: {test.code}\"', 'f\"🔑 Test kodi: <code>{test.code}</code>\"')
src = src.replace('/fast_test <Test Nomi> | <Kalitlar> | <Vaqt(daqiqa)>', '<code>/fast_test &lt;Test Nomi&gt; | &lt;Kalitlar&gt; | &lt;Vaqt(daqiqa)&gt;</code>')
src = src.replace('/fast_test Fizika 9-sinf ChSB | ABCDACBDABCD | 45', '<code>/fast_test Fizika 9-sinf ChSB | ABCDACBDABCD | 45</code>')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated test_creator.py')

# 4. student_test_creator.py
p = 'app/bot/handlers/student/student_test_creator.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('f\"🔑 Test kodi: {test.code}\\n\\n\"', 'f\"🔑 Test kodi: <code>{test.code}</code>\\n\\n\"')
src = src.replace('f\"🔑 Test kodi: {test.code}\"', 'f\"🔑 Test kodi: <code>{test.code}</code>\"')
src = src.replace('f\"✅ Yangi nusxa kodi: {cloned.code}\"', 'f\"✅ Yangi nusxa kodi: <code>{cloned.code}</code>\"')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated student_test_creator.py')

# 5. tests_manage.py
p = 'app/bot/handlers/admin/tests_manage.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('f\"🔑 Test kodi: {test.code}\\n\\n\"', 'f\"🔑 Test kodi: <code>{test.code}</code>\\n\\n\"')
src = src.replace('f\"🔑 Kodi: {cloned.code}\"', 'f\"🔑 Kodi: <code>{cloned.code}</code>\"')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated tests_manage.py')

# 6. guide.py
p = 'app/bot/handlers/student/guide.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('TEST-101 ABCDACBDABCD', '<code>TEST-101 ABCDACBDABCD</code>')
src = src.replace('TEST-101 1a 2b 3c 4d 5a', '<code>TEST-101 1a 2b 3c 4d 5a</code>')
src = src.replace('/fast_test Matematika 10-sinf | ABCDABCD | 40', '<code>/fast_test Matematika 10-sinf | ABCDABCD | 40</code>')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated guide.py')

# 7. quick_check.py
p = 'app/bot/handlers/student/quick_check.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('Misol: {test.code} abcdacbd... yoki {test.code} 1a 2b 3c', 'Misol: <code>{test.code} ABCDACBD...</code>')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated quick_check.py')

# 8. start.py and main_menu.py (Telegram ID in profile view)
p = 'app/bot/handlers/student/main_menu.py'
with open(p, 'r', encoding='utf-8') as f:
    src = f.read()
src = src.replace('f\"🔹 Telegram ID: {user.telegram_id}\\n\"', 'f\"🔹 Telegram ID: <code>{user.telegram_id}</code>\\n\"')
with open(p, 'w', encoding='utf-8') as f:
    f.write(src)
print('Updated main_menu.py')

# Check syntax
for path in ['app/bot/handlers/student/certificates.py', 'app/bot/handlers/student/results.py', 'app/bot/handlers/admin/test_creator.py', 'app/bot/handlers/student/student_test_creator.py', 'app/bot/handlers/admin/tests_manage.py', 'app/bot/handlers/student/guide.py', 'app/bot/handlers/student/quick_check.py', 'app/bot/handlers/student/main_menu.py']:
    with open(path, 'r', encoding='utf-8') as f:
        ast.parse(f.read())
print('ALL SYNTAX VERIFIED OK!')
