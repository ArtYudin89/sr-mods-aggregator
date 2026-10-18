Solar - релиз 2026-10-15
=========================
Распаковать в папку игры, с сохранением путей. Rangers.exe в архиве - собранный билд, под который сделаны нативные DLL (заменит ваш).

Состав:
  Rangers.exe   билд игры 2026-10-06 (Delphi O+), TDS 0x6AC53B97
  Mods\Solar\*   моды Solar (12; SolUtilities обязателен: в нём нативные DLL SolHook/SolEngine и таблицы символов .gsym)
  dsound.dll, XenoCore.dll, XenoNative.ini, XenoNative\Plugins\XenoStable   загрузчик XenoNative (нужен для нативных DLL SolUtilities;
                 если уже установлен - не перезаписывать XenoNative.ini)
Исходники в архив не входят.

Билд игры: только Rangers.exe 2026-10-06 (TDS 0x6AC53B97) из этого архива. Хуки сверяют байты и на другом билде не ставятся.
SolSymbols.6AC53B97.gsym должен лежать рядом с SolEngine.XenoPlugin.dll (Mods\Solar\SolUtilities\Native).

Подключение: в игре включить SolUtilities и нужные Solar-моды (моды Solar зависят от SolUtilities).
Конфликты прописаны в ModuleInfo: SolBigGalaxy / SolCustomGalaxy между собой и с XenoBigGalaxy, RefGalaxyUpgrade*, RefABitMoreStars*, AModGalaxy*;
три раскладки галакарты SolGalamap* между собой; SolMapMarker с AMod_MapMarker; SolFastGen с AModGalaxy*.
Лог нативных DLL - в папке игры (SolHook / SolEngine).
Часть возможностей в игре не проверена.
