import os, re, json, uuid, subprocess, urllib.parse
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response
import yt_dlp

app = Flask(__name__, static_folder='static')
DATA_FILE = Path(__file__).parent / 'data' / 'playlists.json'
COOKIES_FILE = Path(__file__).parent / 'cookies.txt'

def ydl_base():
    o = {'quiet':True,'no_warnings':True,'extractor_retries':3,'socket_timeout':30}
    if COOKIES_FILE.exists(): o['cookiefile'] = str(COOKIES_FILE)
    return o

def load_pls():
    try: return json.loads(DATA_FILE.read_text())
    except: return {"playlists":[]}

def save_pls(data):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

@app.route('/')
def index(): return send_from_directory('static','index.html')

# ── CORS for Spotify OAuth callback ──
@app.after_request
def cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return r

@app.route('/api/search')
def search():
    q = request.args.get('q','').strip()
    if not q: return jsonify([])
    opts = {**ydl_base(), 'extract_flat':True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        r = ydl.extract_info(f"ytsearch20:{q}", download=False)
    out = []
    for e in (r.get('entries') or []):
        if not e: continue
        d = e.get('duration')
        out.append({
            'id': e.get('id'),
            'title': e.get('title','Unknown'),
            'uploader': e.get('uploader') or e.get('channel','Unknown'),
            'duration': f"{int(d)//60}:{int(d)%60:02d}" if d else '–',
            'thumbnail': e.get('thumbnail') or f"https://i.ytimg.com/vi/{e.get('id')}/mqdefault.jpg",
        })
    return jsonify(out)

@app.route('/api/stream')
def stream():
    vid = request.args.get('id','').strip()
    if not vid: return jsonify({'error':'Missing id'}),400
    opts = {**ydl_base(), 'format':'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        d = info.get('duration')
        return jsonify({
            'url': info['url'],
            'title': info.get('title'),
            'uploader': info.get('uploader') or info.get('channel','Unknown'),
            'thumbnail': info.get('thumbnail'),
            'duration': f"{int(d)//60}:{int(d)%60:02d}" if d else '–',
        })
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/download')
def download():
    vid = request.args.get('id','').strip()
    if not vid: return jsonify({'error':'Missing id'}),400
    opts = {**ydl_base(), 'format':'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        ext = info.get('ext','m4a')
        title = re.sub(r'[\\/*?:"<>|]','',info.get('title','audio'))[:80]
        cmd = ['yt-dlp','-f',f'bestaudio[ext={ext}]/bestaudio','--no-warnings']
        if COOKIES_FILE.exists(): cmd += ['--cookies',str(COOKIES_FILE)]
        cmd += ['-o','-',f'https://www.youtube.com/watch?v={vid}']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        ct = 'audio/mp4' if ext=='m4a' else 'audio/webm'
        return Response(proc.stdout, headers={
            'Content-Disposition': f'attachment; filename="{urllib.parse.quote(title)}.{ext}"',
            'Content-Type': ct,
        })
    except Exception as e: return jsonify({'error':str(e)}),500

@app.route('/api/proxy_stream')
def proxy_stream():
    import requests as req
    url = request.args.get('url','')
    if not url: return jsonify({'error':'Missing url'}),400
    hdrs = {'User-Agent':'Mozilla/5.0','Range':request.headers.get('Range','bytes=0-')}
    r = req.get(url, headers=hdrs, stream=True)
    rh = {'Content-Type':r.headers.get('Content-Type','audio/webm'),'Accept-Ranges':'bytes'}
    if 'Content-Range' in r.headers: rh['Content-Range'] = r.headers['Content-Range']
    if 'Content-Length' in r.headers: rh['Content-Length'] = r.headers['Content-Length']
    return Response(r.iter_content(chunk_size=1024*1024), status=r.status_code, headers=rh)

# ── LYRICS (proxy to avoid CORS) ──
@app.route('/api/lyrics')
def lyrics():
    import requests as req
    artist = request.args.get('artist','').strip()
    title  = request.args.get('title','').strip()
    if not artist or not title: return jsonify({'lyrics':None})
    # Clean title: remove parentheses, features, etc.
    clean = re.sub(r'\(.*?\)|\[.*?\]|feat\..*|ft\..*','',title,flags=re.I).strip()
    try:
        r = req.get(
            f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(clean)}",
            timeout=8
        )
        d = r.json()
        return jsonify({'lyrics': d.get('lyrics')})
    except:
        return jsonify({'lyrics':None})

# ── PLAYLISTS ──
@app.route('/api/playlists', methods=['GET'])
def get_playlists(): return jsonify(load_pls())

@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    body = request.get_json()
    data = load_pls()
    pl = {
        'id': str(uuid.uuid4()),
        'name': body.get('name','Nueva playlist'),
        'tracks': body.get('tracks',[]),
        'cover': body.get('cover',''),
        'source': body.get('source','local')
    }
    data['playlists'].append(pl)
    save_pls(data)
    return jsonify(pl)

@app.route('/api/playlists/<pid>', methods=['PUT'])
def update_playlist(pid):
    body = request.get_json()
    data = load_pls()
    for pl in data['playlists']:
        if pl['id'] == pid:
            pl.update({k:v for k,v in body.items() if k!='id'})
            save_pls(data)
            return jsonify(pl)
    return jsonify({'error':'Not found'}),404

@app.route('/api/playlists/<pid>', methods=['DELETE'])
def delete_playlist(pid):
    data = load_pls()
    data['playlists'] = [p for p in data['playlists'] if p['id']!=pid]
    save_pls(data)
    return jsonify({'ok':True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT',5000))
    print(f"\n🎵  Wavr → http://localhost:{port}")
    print(f"🍪  Cookies: {'✅' if COOKIES_FILE.exists() else '❌'}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
