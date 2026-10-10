#!/usr/bin/env python3
"""CLI utility to send in-game notifications / mail / rewards to users.

Usage examples:
  # Broadcast notification with rewards to all users:
  python3 emulator/send_notification.py \
      --title "Thông báo bảo trì máy chủ" \
      --memo "Máy chủ đã hoạt động ổn định trở lại! Tặng bạn 500 Socola và 100 Kẹo." \
      --cp 500 --candy 100

  # Send notification to a specific user:
  python3 emulator/send_notification.py \
      --uuid 0bd31532dbae9377c4914cf97837a28b \
      --title "Quà tặng riêng" \
      --memo "Chúc bạn chơi game vui vẻ!" \
      --cp 1000
"""
import os, sys, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import state
from server.handlers.post import send_post

def main():
    parser = argparse.ArgumentParser(description="Send notification / mail to Guitar Girl player(s)")
    parser.add_argument('--uuid', type=str, default='all', help="Target user UUID (default: 'all')")
    parser.add_argument('--title', type=str, default='Thông báo từ Ban Quản Trị', help="Notification title")
    parser.add_argument('--memo', type=str, default='Cảm ơn bạn đã đồng hành cùng Guitar Girl!', help="Notification memo")
    parser.add_argument('--cp', type=int, default=0, help="Chocolate (CP) reward quantity")
    parser.add_argument('--candy', type=float, default=0.0, help="Candy reward quantity")
    parser.add_argument('--like', type=float, default=0.0, help="Like reward quantity")
    parser.add_argument('--cookie', type=int, default=0, help="Cookie / AP reward quantity")
    parser.add_argument('--guitar', type=int, default=0, help="Guitar ID to attach")
    parser.add_argument('--costume', type=int, default=0, help="Costume ID to attach")
    parser.add_argument('--music', type=int, default=0, help="Music ID to attach")

    args = parser.parse_args()

    items = []
    if args.cp > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': float(args.cp)})
    if args.candy > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 2, 'd_RewardQuantity': float(args.candy)})
    if args.like > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 3, 'd_RewardQuantity': float(args.like)})
    if args.cookie > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 11, 'd_RewardQuantity': float(args.cookie)})
    if args.guitar > 0:
        items.append({'i_RewardType': 9, 'i_RewardId': args.guitar, 'd_RewardQuantity': 1.0})
    if args.costume > 0:
        items.append({'i_RewardType': 3, 'i_RewardId': args.costume, 'd_RewardQuantity': 1.0})
    if args.music > 0:
        items.append({'i_RewardType': 2, 'i_RewardId': args.music, 'd_RewardQuantity': 1.0})

    post = send_post(
        uuid=args.uuid,
        title=args.title,
        memo=args.memo,
        items=items
    )

    if post:
        target_str = f"user '{args.uuid}'" if args.uuid != 'all' else "ALL users (broadcast)"
        print(f"[SUCCESS] Sent notification #{post['idx']} to {target_str}!")
        print(f"Title: {post['title_vi']}")
        print(f"Memo:  {post['memo_vi']}")
        if items:
            print(f"Attached rewards ({len(items)} items):")
            for it in items:
                print(f"  - Type: {it['i_RewardType']}, ID: {it['i_RewardId']}, Qty: {it['d_RewardQuantity']}")
        else:
            print("No rewards attached.")
    else:
        print(f"[ERROR] Failed to send notification (user '{args.uuid}' not found).")
        sys.exit(1)

if __name__ == '__main__':
    main()
