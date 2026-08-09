# План за обединен Harbour пакет за Sublime Text 4

## Резултат и базови версии

- Проектът обединява:
  - текущия пакет от `D:\accounts\st4\Data\Packages\harbour`;
  - `asistex/Sublime-Text-harbour-Package` при commit `694e3d07acdd714409a95e5629d2f10ec1f73768`;
  - `hbmk2` 3.2.1dev от `D:\accounts\hb32_64_zig_v3\bin\hbmk2.exe`;
  - съответстващия source tree `D:\accounts\hb32_64src`.
- Отправната точка от `hbmk2 -find "*"` е 6 239 реда, 6 237 уникални имена и 67 библиотеки. Ново извличане се прави при всяко обновяване, без ръчно поддържани списъци.

## Структура и публични интерфейси

```text
harbour_Sublime_Text_4_Harbour_Syntax_highlighter/
├── PLAN.md, README.md, LICENSE, THIRD_PARTY_NOTICES.md
├── package/Harbour/          # единствената инсталируема ST4 папка
│   ├── Harbour.sublime-syntax
│   ├── completions/
│   ├── snippets/
│   ├── data/function_help.json
│   ├── harbour_help.py
│   └── tests/syntax_test_*
├── catalog/                  # raw inventory, canonical data, overrides, reports
├── tools/                    # extract, generate, validate, package
├── tests/manual/             # визуални тестови файлове и българско ръководство
└── local-only/               # ignored local snapshots, caches and releases
```

- Главният синтаксис е native `.sublime-syntax`, `version: 2`, със scope `source.harbour`.
- Автоматично разпознаваеми разширения: `.prg`, `.hb`, `.ch`, `.ppo`, `.res`, `.idu`. `.c` и `.h` не се присвояват.
- Добавят се две команди: `Harbour: Function Help` и `Harbour: Help for Symbol Under Cursor`.
- Completion записите използват rich completion полетата `trigger`, snippet `contents`, `kind`, `annotation` и `details`.
- Не се пренасят натрапчивите настройки за font, caret и whitespace и машинно зависим build system.

## Синтаксис, функции и помощ

- Grammar-ът се пренаписва с отделни contexts за декларации, изрази, preprocessor, коментари, strings и invalid constructs. Генерираните имена се делят на ограничени regex chunks и се разпознават като извиквания само преди `(`; непараметризирани procedure calls се обработват отделно след `DO`.
- Regression покритието включва коментари; strings; date/timestamp, numeric, logical и `NIL` literals; Harbour оператори; alias/member/macro/by-reference синтаксис; HbPP directives и `.ch` markers; декларации, calls, references и Symbol List; unclosed/stray invalid constructs; copy/paste дефекти; `.res`, `.ppo`, `.hb` и `.idu`.
- Canonical function record съдържа canonical name/casefold key, libraries/installed status, visibility, signature, summary, parameters, return, platform, source version, source path/line/evidence и review status.
- Източниците се прилагат в ред: Harbour `$DOC$`; PRG/HB declarations; `HB_FUNC`, aliases и macro families; проверени локални completions; asistex/curated данни само след source проверка.
- Описанията са кратки собствени резюмета на английски. Всеки help запис минава извличане и повторна проверка спрямо source.
- Всички имена остават в raw inventory и highlighter-а. Име без проверим source е color-only, няма completion/help и се записва в `catalog/reports/source-missing.json`.
- Публичните source-backed функции се показват в autocomplete независимо дали библиотеката е инсталирана; незаредените са означени. Internal/registration symbols не шумят в autocomplete.
- Дубликатите се обединяват с множество provenance записи. Общите snippets се дедуплицират; локалните `help*.sublime-snippet` се пазят в означена `OKT` група след проверка за частни данни. Emoji и HTML-only snippets не влизат в активния пакет.

## Тестове и acceptance критерии

- Native syntax fixtures: comments, strings, literals/operators, declarations/OO, preprocessor `.ch`, DBSTRU `.res`, `.ppo`, `.hb`, `.idu`, invalid constructs и генериран all-functions файл.
- `.res` fixture-ът следва реалния OKT DBSTRU формат, но използва само фиктивни таблици и полета.
- `tests/manual/README_TESTING.bg.md` описва файл, действие, очакван scope/цвят и признак за дефект, плюс auto syntax, comments, symbols, completions, help, snippets, C/C++ non-interference и invalid constructs.
- Python standard-library тестовете проверяват deterministic generation, JSON schema, duplicates, HTML escaping, provenance, review status, regex limits и равенство raw inventory/highlighter set.
- Release acceptance: точен inventory count; пълно highlighter покритие; проверени completion/help полета; missing-source само color-only; native syntax тестове без грешки; all-functions до 2 s и incremental edit под 100 ms на ST4 build 4200; идентични файлове и SHA-256 при повторно генериране.

## Архив, лиценз и GitHub готовност

- Сегашният модул се копира byte-for-byte в `local-only/archive/current-module-20260809/`, включително caches, build файл и snippets.
- Добавят се `ORIGIN.md`, дърво на файловете и `SHA256SUMS.txt`; архивът не участва в генерирането.
- Инсталира се и се пакетира само `package/Harbour`.
- Новият проект е `GPL-3.0-or-later`, със запазени MIT notice за asistex, GPL произход от rafathefull/harbour и отделна provenance за Harbour source/contrib.
- Локалните snapshot-и, caches, временни работни файлове и генерирани `.sublime-package` файлове са събрани в `local-only/` и се изключват с `.gitignore`.
- Преди публикуване се изпълняват secret/path scan, license/notice validation и clean-checkout regeneration.
- Извън първата версия остават Harbour build integration и отделен syntax за `.hbp/.hbc/.hbm`.
