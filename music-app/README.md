# 🎵 Wavr

## Instalación local

```bash
pip install -r requirements.txt
python server.py
# → http://localhost:5000
# → iPhone (misma WiFi): http://<TU_IP>:5000
```

IP local: Windows → `ipconfig` | Mac/Linux → `ifconfig`

---

## 🌐 Dominio gratis + siempre online

### Opción A — Railway (recomendado)
1. Cuenta gratis en https://railway.app
2. Sube la carpeta a GitHub (https://github.com/new)
3. Railway → New Project → Deploy from GitHub → selecciona el repo
4. Railway da una URL tipo `wavr.up.railway.app` — gratis
5. Dominio personalizado gratis: en Railway → Settings → Domains → añade el tuyo

### Opción B — Render (alternativa)
1. https://render.com → New Web Service
2. Conecta tu repo de GitHub
3. Start Command: `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 300`
4. Free tier: se "duerme" tras 15 min de inactividad (se despierta en ~30s)

### Dominio .com gratis
- https://www.freenom.com — dominios .tk .ml .ga gratis
- https://afraid.org — subdominios gratis
- O compra un .com por ~10€/año en Namecheap

### Para Spotify import desde dominio
- Ve a developer.spotify.com/dashboard → tu app → Edit Settings
- Añade tu URL como Redirect URI: `https://tu-dominio.com`

---

## Funciones
- 🔍 Búsqueda YouTube sin anuncios
- ▶️ Streaming + colores dinámicos del álbum
- ⬇️ Descargas rápidas (subprocess pipe)
- 📋 Playlists locales + cola
- 🟢 Import de Spotify (OAuth PKCE, sin backend)
- 📱 iOS nativo: safe areas, full screen player, swipe down
- ⌨️ Atajos: Espacio, ← →
