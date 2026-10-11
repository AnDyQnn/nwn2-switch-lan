# Отладка NWN2 на живой Switch / Live debugging on Switch

**[Русский](#русский) · [English](#english)**

---

## Русский

Инструменты, которыми искались правки LAN-патча. Они нужны, если хотите разобраться, что игра делает на консоли, или перенести патч на другую версию игры. **Обычному игроку они не нужны.**

| Файл | Что делает |
|---|---|
| `nwn2dbg.py` | находит NWN2 на консоли, читает адрес загрузки (ASLR) и запускает gdb с «тихими» брейкпоинтами: при срабатывании печатают регистры и игра идёт дальше; всё пишется в лог |
| `bps_nwn2_lan.txt` | список брейкпоинтов (смещение в `main` + подпись) по сетевому коду: создание игры, выбор транспорта UDP/Photon, рукопожатие NWN-протокола, проверка игрока |
| `gdbproxy.py` | TCP-прокси до gdbstub консоли: нужен, если маршрут до консоли идёт через VPN или другой интерфейс |
| `lanprobe.py` | проверяет с ПК, отвечает ли сервер NWN2 по LAN (пакеты `BNES`/`BNXI` на UDP 5121) |

Смещения в `bps_nwn2_lan.txt` даны для сборки `3554C29951DDA41FE0AF61D3888DC3BB019764CA` (обновление v65536).

### Что понадобится
- **Python 3.8+** на ПК.
- **GDB для AArch64**: `aarch64-none-elf-gdb` из официального [Arm GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads) (Windows: архив `mingw-w64-x86_64-aarch64-none-elf`, нужен только `bin/aarch64-none-elf-gdb.exe`). В репозиторий GDB не включён.
- **Отладчик Atmosphere на консоли.** В `atmosphere/config/system_settings.ini` в секцию `[atmosphere]` добавьте:
  ```ini
  enable_standalone_gdbstub=u8!0x1
  enable_htc=u8!0x0
  ```
  Перезагрузите консоль. После этого она слушает TCP-порт **22225**. Сохраните копию файла до правки, чтобы потом вернуть.

### Как пользоваться
1. Консоль и ПК в одной сети. IP консоли: Настройки → Интернет → Состояние подключения.
2. Если ПК ходит в локальную сеть через VPN, запустите прокси (в отдельном окне):
   ```
   python gdbproxy.py 192.168.1.15 --src <IP вашего ПК в локальной сети>
   ```
   Без VPN прокси не нужен, указывайте `--target 192.168.1.15:22225`.
3. Запустите NWN2 до главного меню и проверьте, что скрипт её видит:
   ```
   python nwn2dbg.py base --gdb путь\к\aarch64-none-elf-gdb.exe
   ```
4. Поставьте ловушки и делайте в игре то, что исследуете (например, Мультиплеер → Новая игра):
   ```
   python nwn2dbg.py trace -o log.txt --gdb путь\к\aarch64-none-elf-gdb.exe
   ```
   В логе будут строки вида
   ```
   HIT CreateGameAndConnect mode=w4 (0 single, 1 UDP, 2 Photon) x0=... x4=1 lr=main+0x650494
   HIT UdpInit OK ...
   ```
5. **Остановка:** `Ctrl+C` в окне gdb, затем `detach` и `quit`. Так gdb уберёт брейкпоинты из памяти игры. Если просто закрыть окно, игра может упасть на первой же оставшейся ловушке.
6. Для двух консолей сразу (сервер + клиент): два прокси на разных портах (`--listen 127.0.0.1:22226`), два `trace` с `--target` и `--tag SRV` / `--tag CLI`.

Проверить LAN-сервер с ПК:
```
python lanprobe.py 192.168.1.15
REPLY BNES b'BNERU\x01\x14\x00...<имя сервера>'
```

### Важно
- Пока gdb подключён, игра работает чуть медленнее; при множестве срабатываний — заметно.
- После работы уберите строки gdbstub из `system_settings.ini` (или верните сохранённую копию) и перезагрузите консоль.
- ASLR: адрес загрузки меняется при каждом запуске игры, поэтому `nwn2dbg.py` читает его заново каждый раз. Перезапустили игру — перезапустите `trace`.

---

## English

The tools used to find the LAN patch. You only need them to study what the game does on the console or to port the patch to another game version. **Players don't need them.**

| File | Purpose |
|---|---|
| `nwn2dbg.py` | finds NWN2 on the console, reads the load address (ASLR) and starts gdb with silent breakpoints that log registers and continue |
| `bps_nwn2_lan.txt` | breakpoint list (offset in `main` + label) for the network code |
| `gdbproxy.py` | TCP proxy to the console gdbstub (useful when the route goes through a VPN) |
| `lanprobe.py` | checks from a PC whether an NWN2 server answers on LAN (`BNES`/`BNXI` on UDP 5121) |

Offsets are for build `3554C29951DDA41FE0AF61D3888DC3BB019764CA` (update v65536).

**Requirements:**
- Python 3.8+.
- `aarch64-none-elf-gdb` from the official [Arm GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads) (not bundled).
- Atmosphere gdbstub: add `enable_standalone_gdbstub=u8!0x1` and `enable_htc=u8!0x0` under `[atmosphere]` in `atmosphere/config/system_settings.ini`, then reboot. The console listens on TCP 22225.

**Usage:**
```
python gdbproxy.py <console-ip> --src <your-lan-ip>        # only if a VPN is in the way
python nwn2dbg.py base  --gdb path/to/aarch64-none-elf-gdb
python nwn2dbg.py trace -o log.txt --gdb path/to/aarch64-none-elf-gdb
python lanprobe.py <host-ip>
```
Stop with `Ctrl+C` → `detach` → `quit` so the breakpoints are removed from game memory. Remove the gdbstub lines from `system_settings.ini` when done.
