import subprocess
import sys
import time

bots = [
    "bot.py",
    "forwarder.py",
    "sender_bot.py.py",
]

processes = {}

def start_bot(name):
    print(f"🚀 Запуск: {name}")
    return subprocess.Popen(
        [sys.executable, "-u", name]
    )

for bot in bots:
    processes[bot] = start_bot(bot)
    time.sleep(2)

print(f"✅ Все {len(bots)} бота запущены")

while True:
    for name, process in list(processes.items()):
        if process.poll() is not None:
            print(
                f"❌ {name} остановился. "
                f"Код: {process.returncode}"
            )

            print(f"🔄 Перезапуск: {name}")
            processes[name] = start_bot(name)

    time.sleep(10)
