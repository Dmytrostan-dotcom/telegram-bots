import subprocess
import sys
import time

bots = [
    "bot.py",
    "bot(2).py",
    "forwarder.py",
    "gipsy.chat.py",
    "osint_bot.py",
    "police_rp.py.py",
    "sender_bot.py.py",
]

processes = []

for bot in bots:
    print(f"🚀 Запуск: {bot}")
    p = subprocess.Popen([sys.executable, "-u", bot])
    processes.append((bot, p))
    time.sleep(2)

print("✅ Все боты запущены")

while True:
    for name, process in processes:
        if process.poll() is not None:
            print(f"❌ {name} завершился с кодом {process.returncode}")
    time.sleep(10)
