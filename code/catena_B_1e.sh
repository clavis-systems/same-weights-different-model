#!/bin/bash
# Deviazione 1e (21/10): le tre corse del caso B rifatte da zero con cache statica e gruppi da 32.
# Aspetta la GPU libera (niente blender.exe, niente lucchetto, memoria < 1500 MiB), guardia a 7,5 GB come la 1d,
# ripartenza automatica come la 1c (al massimo 10 tentativi per condizione; il gruppo interrotto si rifa').
# Esce con 0 solo se tutte e tre le condizioni hanno 1.319 righe.
W="C:/Users/emari/Desktop/MIA IA LOCALE/.claude/worktrees/procedural-maps-from-objects-ddefb0"
PY="C:/Users/emari/Desktop/MIA IA LOCALE/registro-env/Scripts/python.exe"
R="$W/strumenti/risultati/stessi_pesi"
E="$R/effetto"
L="$E/catena_B_1e.log"
K="C:/Users/emari/Desktop/MIA IA LOCALE/strumenti/risultati/.gpu_lock"
LIM=1319
echo "=== avvio catena B 1e $(date '+%d/%m %H:%M:%S'), aspetto la GPU libera" >> "$L"
liberi=0
while [ $liberi -lt 3 ]; do
  b=$(tasklist //FI "IMAGENAME eq blender.exe" 2>/dev/null | grep -ci blender)
  m=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d '\r ')
  if [ "$b" = "0" ] && [ ! -f "$K" ] && [ "${m:-9999}" -lt 1500 ]; then liberi=$((liberi+1)); else liberi=0; fi
  sleep 30
done
cd "$W/strumenti/scoperta/stessi_pesi" || exit 1
rm -f "$E/STOP_B"
echo "=== GPU libera $(date '+%H:%M:%S')" >> "$L"
( while true; do
    M=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d '\r ')
    echo "$(date '+%H:%M:%S') ${M} MiB" >> "$E/memoria_B_1e.log"
    if [ "${M:-0}" -gt 7500 ]; then
      touch "$E/STOP_B"
      echo "$(date '+%H:%M:%S') STOP: memoria ${M} MiB > 7500 durante B" >> "$L"
      powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*effetto.py genera*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force }" >/dev/null 2>&1
    fi
    sleep 30
  done ) &
SORV=$!
corri() {
  cond=$1
  for t in 1 2 3 4 5 6 7 8 9 10; do
    [ -f "$E/STOP_B" ] && return
    while [ -f "$K" ]; do sleep 30; done
    n=$(cat "$E/B_$cond.jsonl" 2>/dev/null | wc -l)
    [ "$n" -ge "$LIM" ] && break
    echo "--- B $cond tentativo $t, righe $n, $(date '+%H:%M:%S')" >> "$L"
    "$PY" -X utf8 effetto.py genera "$R/corsa1" B $cond --out "$E" --limite $LIM --lotto 32 --cache-statica > "$E/err_B_${cond}_1e_$t.log" 2>&1
    echo "    uscita $? $(date '+%H:%M:%S')" >> "$L"
  done
  echo "=== B $cond: $(cat "$E/B_$cond.jsonl" 2>/dev/null | wc -l) righe $(date '+%H:%M:%S')" >> "$L"
}
for cond in prima dopo controllo; do corri $cond; done
kill $SORV 2>/dev/null
ok=1
for cond in prima dopo controllo; do
  [ "$(cat "$E/B_$cond.jsonl" 2>/dev/null | wc -l)" -ge "$LIM" ] || ok=0
done
echo "=== fine B 1e $(date '+%H:%M:%S'), complete: $ok" >> "$L"
[ $ok = 1 ]
