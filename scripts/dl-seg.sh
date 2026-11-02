#!/usr/bin/env bash
# 分段下载器：用多个全新 curl 连接绕过 MITM 代理对单连接的限速/尾段卡死
# 用法: dl-seg.sh <url> <outfile> [segments]
set -u
URL="$1"; OUT="$2"; SEG="${3:-8}"
if [ -z "$URL" ] || [ -z "$OUT" ]; then echo "usage: dl-seg.sh URL OUT [SEG]"; exit 2; fi
DIR="$(dirname "$OUT")"; BASE="$(basename "$OUT")"
TMP="$DIR/.seg_$BASE"
rm -rf "$TMP"; mkdir -p "$TMP"

# 取总大小（跟随重定向，取最后一个 content-length）
SIZE=$(curl -k -sI -L --max-time 90 "$URL" | tr -d '\r' | awk -F': ' 'tolower($1)=="content-length"{v=$2} END{print v}' | tr -d ' ')
if ! [[ "$SIZE" =~ ^[0-9]+$ ]] || [ "$SIZE" -le 0 ]; then
  echo "[$BASE] 无法获取大小，退化为单流续传"
  curl -k -L --retry 8 --retry-delay 3 -C - -o "$OUT" "$URL"
  echo "[$BASE] 单流完成 rc=$? size=$(stat -c%s "$OUT" 2>/dev/null)"
  exit $?
fi
echo "[$BASE] 总大小=$SIZE 段数=$SEG"

CHUNK=$(( (SIZE + SEG - 1) / SEG ))
PIDS=()
for i in $(seq 0 $((SEG-1))); do
  START=$(( i * CHUNK ))
  END=$(( START + CHUNK - 1 ))
  [ "$i" -eq $((SEG-1)) ] && END=$((SIZE-1))
  curl -k -s -L --retry 8 --retry-delay 3 -r "${START}-${END}" "$URL" -o "$TMP/part_$i" &
  PIDS[$i]=$!
done

FAIL=0
for i in $(seq 0 $((SEG-1))); do
  if ! wait ${PIDS[$i]}; then echo "[$BASE] 第 $i 段失败"; FAIL=1; fi
done
if [ "$FAIL" -ne 0 ]; then echo "[$BASE] 存在失败段"; exit 1; fi

# 按数字顺序拼接（不能用通配符，避免字典序错乱）
: > "$OUT"
for i in $(seq 0 $((SEG-1))); do cat "$TMP/part_$i" >> "$OUT"; done
FINAL=$(stat -c%s "$OUT" 2>/dev/null)
rm -rf "$TMP"
if [ "$FINAL" = "$SIZE" ]; then
  echo "[$BASE] OK 大小=$FINAL"
else
  echo "[$BASE] 大小不符 got=$FINAL expected=$SIZE"
  exit 1
fi
