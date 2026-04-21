import os, re, json, uuid, subprocess, urllib.parse
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
import yt_dlp

app = Flask(__name__, static_folder='static')
DATA_FILE = Path(__file__).parent / 'data' / 'playlists.json'

def load_playlists():
    try: return json.loads(DATA_FILE.read_text())
    except: return {"playlists": []}

def save_playlists(data):
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ── STATIC ────────────────────────────────────────
@app.route('/')
def index(): return send_from_directory('static', 'index.html')

# ── SEARCH ────────────────────────────────────────
@app.route('/api/search')
def search():
    q = request.args.get('q', '').strip()
    if not q: return jsonify([])
    opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        r = ydl.extract_info(f"ytsearch20:{q}", download=False)
    out = []
    for e in r.get('entries', []):
        if not e: continue
        d = e.get('duration')
        out.append({
            'id': e.get('id'), 'title': e.get('title','Unknown'),
            'uploader': e.get('uploader') or e.get('channel','Unknown'),
            'duration': f"{int(d)//60}:{int(d)%60:02d}" if d else '–',
            'thumbnail': e.get('thumbnail') or f"https://i.ytimg.com/vi/{e.get('id')}/mqdefault.jpg",
        })
    return jsonify(out)

# ── STREAM ────────────────────────────────────────
@app.route('/api/stream')
def stream():
    vid = request.args.get('id','').strip()
    if not vid: return jsonify({'error':'Missing id'}), 400
    opts = {'quiet':True,'no_warnings':True,'format':'bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        d = info.get('duration')
        return jsonify({
            'url': info['url'], 'title': info.get('title'),
            'uploader': info.get('uploader') or info.get('channel','Unknown'),
            'thumbnail': info.get('thumbnail'),
            'duration': f"{int(d)//60}:{int(d)%60:02d}" if d else '–',
            'ext': info.get('ext','webm'),
        })
    except Exception as e: return jsonify({'error':str(e)}), 500

# ── DOWNLOAD (subprocess pipe = fast) ─────────────
@app.route('/api/download')
def download():
    vid = request.args.get('id','').strip()
    if not vid: return jsonify({'error':'Missing id'}), 400
    opts = {'quiet':True,'no_warnings':True,'format':'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio'}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        ext = info.get('ext','m4a')
        title = re.sub(r'[\\/*?:"<>|]','',info.get('title','audio'))[:80]
        cmd = ['yt-dlp','-f',f'bestaudio[ext={ext}]/bestaudio','--no-warnings','-o','-',
               f'https://www.youtube.com/watch?v={vid}']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        ct = 'audio/mp4' if ext=='m4a' else 'audio/webm'
        return Response(proc.stdout, headers={
            'Content-Disposition': f'attachment; filename="{urllib.parse.quote(title)}.{ext}"',
            'Content-Type': ct,
        })
    except Exception as e: return jsonify({'error':str(e)}), 500

# ── PROXY STREAM ──────────────────────────────────
@app.route('/api/proxy_stream')
def proxy_stream():
    import requests as req
    url = request.args.get('url','')
    if not url: return jsonify({'error':'Missing url'}), 400
    hdrs = {'User-Agent':'Mozilla/5.0','Range':request.headers.get('Range','bytes=0-')}
    r = req.get(url, headers=hdrs, stream=True)
    rh = {'Content-Type':r.headers.get('Content-Type','audio/webm'),'Accept-Ranges':'bytes'}
    if 'Content-Range' in r.headers: rh['Content-Range'] = r.headers['Content-Range']
    if 'Content-Length' in r.headers: rh['Content-Length'] = r.headers['Content-Length']
    return Response(r.iter_content(chunk_size=1024*1024), status=r.status_code, headers=rh)

# ── PLAYLISTS (local storage) ──────────────────────
@app.route('/api/playlists', methods=['GET'])
def get_playlists():
    return jsonify(load_playlists())

@app.route('/api/playlists', methods=['POST'])
def create_playlist():
    body = request.get_json()
    data = load_playlists()
    pl = {'id': str(uuid.uuid4()), 'name': body.get('name','Nueva playlist'),
          'tracks': body.get('tracks', []), 'cover': body.get('cover',''),
          'source': body.get('source','local')}
    data['playlists'].append(pl)
    save_playlists(data)
    return jsonify(pl)

@app.route('/api/playlists/<pid>', methods=['PUT'])
def update_playlist(pid):
    body = request.get_json()
    data = load_playlists()
    for pl in data['playlists']:
        if pl['id'] == pid:
            pl.update({k:v for k,v in body.items() if k != 'id'})
            save_playlists(data)
            return jsonify(pl)
    return jsonify({'error':'Not found'}), 404

@app.route('/api/playlists/<pid>', methods=['DELETE'])
def delete_playlist(pid):
    data = load_playlists()
    data['playlists'] = [p for p in data['playlists'] if p['id'] != pid]
    save_playlists(data)
    return jsonify({'ok':True})

# ── RUN ───────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🎵  Wavr → http://localhost:{port}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
