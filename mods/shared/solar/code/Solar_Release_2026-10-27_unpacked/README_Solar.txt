Solar - релиз 2026-10-27
========================
Установка: распаковать в папку игры с заменой. Папка Mods\Solar добавляется к имеющимся модам.

Состав:
  Mods\Solar\*   моды Solar (15): SolBigGalaxy, SolCountKeypad, SolCustomGalaxy, SolFastGen, SolGalamapFullHD, SolGalamapHD, SolABWeapons, SolABLoadouts, SolABTranc, SolMapMarker, SolMapZoom, SolNextDayFast, SolShopCompare, SolSpaceZoom, SolUtilities.
                 SolUtilities обязателен: в нём лежат DLL SolHook/SolEngine и таблицы символов .gsym.
  Rangers.exe    пересборка разработчика 2026-10-26 (TDS 0x6ADF851C): исходники 2026-10-06 + исправление CRC (jge -> jae в двух функциях).
                 Перед заменой сохраните свой Rangers.exe. Для этого exe в SolUtilities есть таблица SolSymbols.6ADF851C.gsym
                 с отпечатками функций и картой групп хуков: при старте SolHook сверяет каждую хукаемую функцию и отключает
                 группу, которая не совпала (сигнал, окно и запись в SolHook.log).
  dsound.dll, XenoCore.dll, XenoNative.ini, XenoNative\Plugins\XenoStable   загрузчик XenoNative (нужен для нативных DLL SolUtilities;
                 если он уже установлен - не перезаписывайте свой XenoNative.ini)
Исходные тексты (.txt) и скрипты (.rson) в архив не входят.

Билды: таблицы лежат для трёх сборок Rangers.exe - 0x6ADF851C (в комплекте), 0x6AC53B97 (2026-10-06) и 0x6A7AFC5C (август);
нужная выбирается по TDS exe при старте.

Зависимости: SolUtilities нужен всем, кроме SolGalamapHD и SolMapMarker. SolABLoadouts и SolABTranc требуют SolABWeapons.
SolMapMarker сам по себе не зависит от раскладки галакарты, но кнопки подогнаны под SolGalamapHD / SolGalamapFullHD.
Конфликты (ModuleInfo): SolBigGalaxy и SolCustomGalaxy - друг с другом и с XenoBigGalaxy, RefGalaxyUpgrade*, RefABitMoreStars*, AModGalaxy*;
раскладки SolGalamapHD и SolGalamapFullHD - друг с другом; SolMapMarker - с AMod_MapMarker.
Настройки и описания - в Lang мода (CFG\Rus\Lang.txt, блоки DLLSettings.*), для изменения нужна пересборка .dat.

Изменения 2026-10-27:
  * Rangers.exe 2026-10-26 включён в комплект (раньше релиз шёл без exe).
  * ModuleInfo всех модов переписаны по единым правилам: краткое описание содержит строку, можно ли подключать/отключать мод
    в течение партии (зелёное слово - можно, красное - нельзя), полное описание и английский перевод приведены в соответствие,
    конфликты и зависимости перепроверены. Метки "в течение партии" расставлены по составу мода и в игре пока не проверены.
  * Мод SolGalamap1280x1024 удалён из сборника.
Изменения 2026-10-26:
  * Исправлено "Integrity check fail" при загрузке/сохранении: CRC мог считаться неверно, когда границы данных попадали
    на область со знаком; хук SaveCrc включён (Lang DLLSettings.BugFix.SaveCrc=1).
  * Диагностика (Lang DLLSettings.Diag.SaveCrc=1, выключена): в SolHook.log пишутся строки "save_crc BIG|SPAN ...".
  * Лог: порты NextDay пишут не в nextday_engine.log, а в общий SolHook.log.
  * SolNextDayFast: DayProfile=0 (профайлер по дням выключен).
