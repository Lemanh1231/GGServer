import os, json, time
from server import state
from server.handlers.registry import cmd, OK, _payload

_BROADCAST_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'broadcast_posts.json')

def _load_broadcast_posts():
    if not os.path.exists(_BROADCAST_PATH):
        return []
    try:
        with open(_BROADCAST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _save_broadcast_posts(posts):
    try:
        with open(_BROADCAST_PATH, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def send_post(uuid=None, title='Thông báo', memo='', items=None, notice_type=1):
    """Send an in-game post/notification to a specific user or broadcast to all users."""
    now = int(time.time())
    item_list = []
    if items:
        for it in items:
            item_list.append({
                'i_RewardType': it.get('i_RewardType', 1),
                'i_RewardId': it.get('i_RewardId', 1),
                'd_RewardQuantity': float(it.get('d_RewardQuantity', 1.0))
            })

    broadcasts = _load_broadcast_posts()
    all_indices = [100] + [p.get('idx', 100) for p in broadcasts]
    target_user = None
    if uuid and uuid != 'all':
        target_user = state.get_user(uuid)
        if not target_user:
            return None
        all_indices.extend(p.get('idx', 0) for p in target_user.get('posts', []) if p.get('idx'))
        all_indices.extend(target_user.get('deleted_post_indices', []))

    next_idx = max(all_indices) + 1

    post = {
        'idx': next_idx,
        'notice_type': notice_type,
        'title_ko': title,
        'memo_ko': memo,
        'title_en': title,
        'memo_en': memo,
        'title_jp': title,
        'memo_jp': memo,
        'title_zh_chs': title,
        'memo_zh_chs': memo,
        'title_zh_cht': title,
        'memo_zh_cht': memo,
        'title_vi': title,
        'memo_vi': memo,
        'title_es': title,
        'memo_es': memo,
        'title_it': title,
        'memo_it': memo,
        'title_id': title,
        'memo_id': memo,
        'title_th': title,
        'memo_th': memo,
        'title_pt': title,
        'memo_pt': memo,
        'title_hi': title,
        'memo_hi': memo,
        'have_reward': 1 if item_list else 0,
        'status': 0,
        'unlimit_flg': 0,
        'flg': 0,
        'create_time': now,
        'del_time': now + 86400 * 30,
        'item_list': item_list,
        'url': '',
        'image_resource_name': '',
    }

    if target_user:
        posts = target_user.setdefault('posts', [])
        posts.append(post)
        state.save_user(target_user)
        return post
    else:
        broadcasts.append(post)
        _save_broadcast_posts(broadcasts)
        conn = state.get_db()
        rows = conn.execute('SELECT uuid FROM user_data').fetchall()
        conn.close()
        for r in rows:
            u = state.get_user(r['uuid'])
            if u:
                posts = u.setdefault('posts', [])
                if not any(p.get('idx') == next_idx for p in posts):
                    posts.append(dict(post))
                    state.save_user(u)
        return post

def _default_welcome_post(now):
    return {
        'idx': 1,
        'notice_type': 1,
        'title_ko': '기타소녀에 오신 것을 환영합니다!',
        'memo_ko': '기타소녀와 함께 힐링 음악 여행을 떠나보세요.',
        'title_en': 'Welcome to Guitar Girl!',
        'memo_en': 'Thank you for playing Guitar Girl! Enjoy your peaceful guitar melodies.',
        'title_jp': 'ギター少女へようこそ！',
        'memo_jp': 'ギター少女と一緒に心癒される音楽の旅へ。',
        'title_zh_chs': '欢迎来到吉他少女！',
        'memo_zh_chs': '欢迎和吉他少女一起开启治愈音乐之旅。',
        'title_zh_cht': '歡迎來到吉他少女！',
        'memo_zh_cht': '歡迎和吉他少女一起開啟療癒音樂之旅。',
        'title_vi': 'Chào mừng đến với Guitar Girl!',
        'memo_vi': 'Cảm ơn bạn đã tham gia cùng cô gái guitar! Chúc bạn có những phút giây thư giãn tuyệt vời cùng âm nhạc.',
        'title_es': '¡Te damos la bienvenida a Guitar Girl!',
        'memo_es': '¡Disfruta de la música relajante junto a Guitar Girl!',
        'title_it': 'Benvenuta in Guitar Girl!',
        'memo_it': 'Goditi la musica rilassante con Guitar Girl!',
        'title_id': 'Selamat datang di Gadis Gitar!',
        'memo_id': 'Nikmati musik santai bersama Gadis Gitar!',
        'title_th': 'ยินดีต้อนรับสู่สาวนักกีตาร์!',
        'memo_th': 'เพลิดเพลินไปกับเสียงเพลงอันผ่อนคลายกับสาวนักกีตาร์!',
        'title_pt': 'Bem-vindo ao Menina guitarrista!',
        'memo_pt': 'Aproveite a música relaxante com a Menina guitarrista!',
        'title_hi': 'गिटार गर्ल में आपका स्वागत है!',
        'memo_hi': 'गिटार गर्ल के साथ मधुर संगीत का आनंद लें।',
        'have_reward': 1,
        'status': 0,
        'unlimit_flg': 0,
        'flg': 0,
        'create_time': now,
        'del_time': now + 86400 * 30,
        'item_list': [
            {'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': 1000.0},
            {'i_RewardType': 1, 'i_RewardId': 2, 'd_RewardQuantity': 500.0},
        ],
        'url': '',
        'image_resource_name': '',
    }

def _get_user_posts(user):
    now = int(time.time())
    posts = user.setdefault('posts', [])
    dirty = False

    deleted_indices = set(user.get('deleted_post_indices', []))
    if 0 in deleted_indices:
        deleted_indices.discard(0)
        user['deleted_post_indices'] = list(deleted_indices)
        dirty = True

    # Purge any posts that have been deleted
    if any(p.get('idx') in deleted_indices for p in posts):
        posts = [p for p in posts if p.get('idx') not in deleted_indices]
        user['posts'] = posts
        dirty = True

    # Normalize existing posts:
    # If a post has no unclaimed reward or is marked status 1,
    # client expects BOTH status=1 (claimed/processed) AND flg=1 (read),
    # otherwise client's AnyoneConfirm() checks flg at offset 0x1A and sees unread mail!
    for p in posts:
        if p.get('status') == 1 or p.get('have_reward') == 0:
            if p.get('have_reward') == 0 and p.get('status') != 1:
                p['status'] = 1
                dirty = True
            if p.get('flg') != 1:
                p['flg'] = 1
                dirty = True

    if not posts and not user.get('welcome_post_sent'):
        posts.append(_default_welcome_post(now))
        user['welcome_post_sent'] = True
        dirty = True

    existing_indices = {p.get('idx') for p in posts if p.get('idx')}
    broadcasts = _load_broadcast_posts()
    for bp in broadcasts:
        b_idx = bp.get('idx')
        if b_idx not in existing_indices and b_idx not in deleted_indices:
            user_post = dict(bp)
            user_post['status'] = bp.get('status', 0)
            user_post['flg'] = bp.get('flg', 0)
            posts.append(user_post)
            existing_indices.add(b_idx)
            dirty = True

    if dirty:
        state.save_user(user)
    return posts


@cmd('getPostTime')
def h_get_post_time(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if user:
        posts = _get_user_posts(user)
        latest_time = max((post.get('create_time', 0) for post in posts), default=0)
    else:
        latest_time = 0
    return {'time': latest_time}, OK

@cmd('getPost')
def h_get_post(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    now = int(time.time())
    if user:
        posts = _get_user_posts(user)
    else:
        posts = []
    return {
        'server_time': now,
        'post_list': posts,
    }, OK

@cmd('providePost')
def h_provide_post(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    idx = int(p.get('idx', 0) or 0)
    user = state.get_user(uuid)
    granted_items = []
    if user:
        user['welcome_post_sent'] = True
        posts = _get_user_posts(user)
        for post in posts:
            if post.get('idx') == idx:
                if post.get('have_reward') == 1:
                    ud = user['userdata']
                    cp_add = 0
                    candy_add = 0.0
                    for item in post.get('item_list', []):
                        granted_items.append(item)
                        rtype = item.get('i_RewardType', 0)
                        rid = item.get('i_RewardId', 0)
                        qty = float(item.get('d_RewardQuantity', 0))
                        if rtype in (1, 11):
                            if rid == 1: # Chocolate (Socola)
                                cp_add += int(qty)
                                ud['u_cp'] = int(ud.get('u_cp', 0) or 0) + int(qty)

                            elif rid == 2: # Candy (Kẹo)
                                candy_add += qty
                                ud['u_candy'] = ud.get('u_candy', 0.0) + qty
                            elif rid in (3, 4): # Like (Lượt thích)
                                ud['u_like'] = ud.get('u_like', 0.0) + qty
                                state.increment_currency(uuid, like=qty)
                            elif rid == 8: # Fans
                                ud['u_fans'] = ud.get('u_fans', 0) + int(qty)
                                state.increment_currency(uuid, fans=int(qty))
                            elif rid == 11: # Cookie (Bánh quy)
                                state.add_ap(user, int(qty))
                        elif rtype == 2: # Music
                            musics = user.setdefault('user_music', [])
                            if not any(int(m.get('i_id', 0) or 0) == rid for m in musics):
                                musics.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0})
                        elif rtype == 3: # Costume
                            costumes = user.setdefault('costumes', [])
                            if not any(int(c.get('i_id', 0) or 0) == rid for c in costumes):
                                costumes.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0})
                        elif rtype == 4: # Prop
                            props = user.setdefault('user_prop', [])
                            if not any(int(p.get('i_id', 0) or 0) == rid for p in props):
                                props.append({'i_id': rid, 'i_Level': 1})
                        elif rtype == 9: # Guitar
                            guitars = user.setdefault('user_guitar', [])
                            if not any(int(g.get('i_id', 0) or 0) == rid for g in guitars):
                                guitars.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0})
                    if uuid and (cp_add or candy_add):
                        state.increment_currency(uuid, cp=cp_add, candy=candy_add)
                    post['have_reward'] = 0
                    post['status'] = 1
                    post['flg'] = 1
                    state.save_user(user)
                break
    return granted_items, OK

@cmd('readPost')
def h_read_post(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    idx = int(p.get('idx', 0) or 0)
    user = state.get_user(uuid)
    if user:
        posts = _get_user_posts(user)
        for post in posts:
            if post.get('idx') == idx:
                post['status'] = 1
                post['flg'] = 1
                state.save_user(user)
                break
    return {'idx': idx}, OK

@cmd('deletePost')
def h_delete_post(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    idx = int(p.get('idx', 0) or 0)
    type_ = int(p.get('type', 0) or 0)
    user = state.get_user(uuid)
    if user:
        user['welcome_post_sent'] = True
        posts = user.setdefault('posts', [])
        del_set = set(user.setdefault('deleted_post_indices', []))
        del_set.discard(0)
        if idx == 0 or type_ == 1:
            # Delete all read/claimed mail
            remaining_posts = []
            for post in posts:
                # Any post where reward has been claimed (have_reward == 0) and is read (status == 1 or flg == 1)
                if post.get('have_reward') == 0 and (post.get('status') == 1 or post.get('flg') == 1):
                    p_idx = post.get('idx')
                    if p_idx:
                        del_set.add(p_idx)
                else:
                    remaining_posts.append(post)
            user['posts'] = remaining_posts
        else:
            user['posts'] = [post for post in posts if post.get('idx') != idx]
            if idx:
                del_set.add(idx)
        user['deleted_post_indices'] = list(del_set)
        state.save_user(user)
    return {'idx': idx}, OK

