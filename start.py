import subprocess
import sys
import time

bots = [
    "bot.py",
    "bot(2).py",
    "forwarder.py",
    "gipsy.chat.py",
    "sender_bot.py.py",
]

processes = []

for bot in bots:
    print(f"🚀 Запуск: {bot}")
    process = subprocess.Popen([sys.executable, "-u", bot])
    processes.append((bot, process))
    time.sleep(2)

print("✅ Все 5 ботов запущены")

while True:
    for name, process in processes:
        if process.poll() is not None:
            print(f"❌ {name} остановился. Код: {process.returncode}")
    time.sleep(10)
