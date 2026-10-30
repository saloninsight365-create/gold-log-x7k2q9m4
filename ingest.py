#!/usr/bin/env python3
"""MT5の履歴(貼り付けテキスト)を trades.json に追記・更新する。

使い方: python3 -I ingest.py <貼り付けテキスト> <trades.json>
同じチケット番号は上書き、新しいものは追加。決済時刻の順に並べて保存する。
"""
import json
import os
import sys
from datetime import datetime


def num(s):
    return float(s.replace(",", "").replace("+", ""))


def when(s):
    return datetime.strptime(s, "%d/%m/%Y %H:%M:%S")


def round_half_up(x, digits=2):
    f = 10 ** digits
    return int(x * f + 0.5) / f if x >= 0 else -int(-x * f + 0.5) / f


def parse(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    i = 0
    while i < len(lines):
        if lines[i] not in ("B", "S"):
            i += 1
            continue
        b = lines[i : i + 12]
        if len(b) < 11:
            raise ValueError("途中で終わっている取引があります: " + " / ".join(b))
        side, symbol, vol, op, cl, profit = b[0], b[1], b[2], b[3], b[4], b[5]
        # 並び: side, symbol, vol/vol, 建値, 決済値, 損益, 損益, 手数料/スワップ, 開始, 決済, #チケット, 状態
        opened = when(b[8])
        closed = when(b[9])
        ticket = b[10].lstrip("#")
        lots = float(vol.split("/")[0])
        open_price, close_price = num(op), num(cl)
        move = (close_price - open_price) if side == "B" else (open_price - close_price)
        hold = (closed - opened).total_seconds() / 60
        out.append(
            {
                "ticket": ticket,
                "date": closed.strftime("%Y-%m-%d"),
                "time": closed.strftime("%H:%M"),
                "hold_min": round_half_up(hold, 1),
                "side": "買い" if side == "B" else "売り",
                "lots": lots,
                "open_price": open_price,
                "close_price": close_price,
                "move": round_half_up(move, 2),
                "profit": num(profit),
                "symbol": symbol,
                "opened_at": opened.strftime("%Y-%m-%d %H:%M:%S"),
                "closed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        i += 12 if len(b) >= 12 and b[11] not in ("B", "S") else 11
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        new = parse(f.read())
    old = []
    if os.path.exists(dst):
        with open(dst, encoding="utf-8") as f:
            old = json.load(f)
    by_ticket = {t["ticket"]: t for t in old}
    added = 0
    for t in new:
        if t["ticket"] not in by_ticket:
            added += 1
        by_ticket[t["ticket"]] = t
    rows = sorted(by_ticket.values(), key=lambda t: t["closed_at"])
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    n = len(rows)
    net = round(sum(t["profit"] for t in rows), 2)
    wins = sum(1 for t in rows if t["profit"] > 0)
    losses = sum(1 for t in rows if t["profit"] < 0)
    print(f"読み込み {len(new)} 件 / 新規 {added} 件 / 合計 {n} 件")
    print(f"累計 {net:+.2f} / 勝ち {wins} / 負け {losses} / ±0 {n - wins - losses}")


if __name__ == "__main__":
    main()
