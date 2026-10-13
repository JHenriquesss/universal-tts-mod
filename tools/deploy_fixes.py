import os
import shutil

with open('renpy_mod/tts_mod.rpy', 'r', encoding='utf-8') as f:
    mod_content = f.read()

# 1. OriginStoryS2
orig_dir = r'D:\Games\OriginStoryS2-0.10.1-pc\OriginStoryS2-0.10.1-pc\game'
if os.path.isdir(orig_dir):
    orig_mod = mod_content.replace('TTS_VOICE = "af_heart"', 'TTS_VOICE = "am_onyx"')
    with open(os.path.join(orig_dir, 'tts_mod.rpy'), 'w', encoding='utf-8') as f:
        f.write(orig_mod)
    shutil.copy2('renpy_mod/tts_engines.py', os.path.join(orig_dir, 'tts_engines.py'))
    rpyc = os.path.join(orig_dir, 'tts_mod.rpyc')
    if os.path.exists(rpyc):
        try:
            os.remove(rpyc)
        except Exception:
            pass
    print('Deploy to OriginStoryS2 successful.')

# 2. MyGirlfriendsFriends
mgf_dir = r'D:\Games\MyGirlfriendsFriends-2.5-pc\MyGirlfriendsFriends-2.5-pc\game'
if os.path.isdir(mgf_dir):
    mgf_mod = mod_content.replace('TTS_VOICE = "af_heart"', 'TTS_VOICE = "am_onyx"')
    with open(os.path.join(mgf_dir, 'tts_mod.rpy'), 'w', encoding='utf-8') as f:
        f.write(mgf_mod)
    shutil.copy2('renpy_mod/tts_engines.py', os.path.join(mgf_dir, 'tts_engines.py'))
    rpyc = os.path.join(mgf_dir, 'tts_mod.rpyc')
    if os.path.exists(rpyc):
        try:
            os.remove(rpyc)
        except Exception:
            pass
    print('Deploy to MyGirlfriendsFriends successful.')
