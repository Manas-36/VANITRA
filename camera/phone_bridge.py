"""Phone camera -> laptop, and the decoded text back to the phone. No app to install on the phone.

The laptop runs a small HTTPS + WebSocket server. Open the printed address on the phone (same Wi-Fi or the
laptop's hotspot), accept the self-signed certificate warning once, allow the camera. The phone streams
JPEG frames; the laptop sends back live glosses and finished sentences, which the phone shows in large text
and can SPEAK aloud (phone text-to-speech), so the hearing person can listen or read.

Used by live.py and record.py (`--source phone`). Run alone to test the link:
    python camera/phone_bridge.py            # shows how many frames arrive per second
Needs: pip install aiohttp cryptography opencv-python
"""
import asyncio
import datetime
import ipaddress
import json
import os
import queue
import socket
import ssl
import struct
import threading
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(HERE, ".cert")

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Vanitra camera</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--ink:#f0f3f6;--mut:#8b949e;--acc:#2dd4bf;--warn:#f59e0b}
*{box-sizing:border-box}html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{display:flex;flex-direction:column;height:100%;padding:12px;gap:10px;max-width:900px;margin:auto}
#vid{width:100%;max-height:42vh;object-fit:cover;border-radius:14px;background:#000}
#vid.mirror{transform:scaleX(-1)}
.row{display:flex;gap:8px;flex-wrap:wrap}
button{flex:1;min-width:90px;padding:12px 10px;border-radius:12px;border:1px solid #30363d;background:var(--card);
color:var(--ink);font-size:15px;font-weight:600}
button.on{background:var(--acc);color:#04201c;border-color:var(--acc)}
#status{color:var(--mut);font-size:13px}
#prompt{display:none;padding:14px;border-radius:12px;background:var(--warn);color:#1b1300;font-size:22px;
font-weight:800;text-align:center}
#live{min-height:2.2em;font-size:20px;color:var(--acc);letter-spacing:.04em}
#top{color:var(--mut);font-size:14px;min-height:1.2em}
#sent{flex:1;overflow:auto;background:var(--card);border-radius:14px;padding:14px;font-size:26px;line-height:1.35}
#sent p{margin:0 0 10px}#sent p.g{font-size:13px;color:var(--mut);margin-top:-8px}
</style></head><body><main>
<video id="vid" autoplay playsinline muted class="mirror"></video>
<div class="row"><button id="go" class="on">Start</button><button id="flip">Flip camera</button>
<button id="speak" class="on">Speak: on</button><button id="clear">Clear</button></div>
<div id="status">connecting...</div>
<div id="prompt"></div>
<div id="live"></div><div id="top"></div>
<div id="sent"></div>
</main><script>
const $=id=>document.getElementById(id);
let ws, stream, facing='user', running=false, speakOn=true, inflight=0, sent=0, t0=performance.now(), lat=0;
const canvas=document.createElement('canvas'), ctx=canvas.getContext('2d');
function connect(){
  ws=new WebSocket(`wss://${location.host}/ws`); ws.binaryType='arraybuffer';
  ws.onopen=()=>{$('status').textContent='connected'; if(!stream) start();};
  ws.onclose=()=>{$('status').textContent='disconnected - retrying'; setTimeout(connect,1500);};
  ws.onmessage=e=>{const m=JSON.parse(e.data);
    if(m.type==='ack'){inflight=Math.max(0,inflight-1); lat=performance.now()-m.t;}
    else if(m.type==='partial'){$('live').textContent=(m.glosses||[]).join(' ');
      $('top').textContent=(m.top||[]).map(x=>`${x[0]} ${Math.round(x[1]*100)}%`).join('   ');}
    else if(m.type==='sentence'){const p=document.createElement('p');p.textContent=m.text;
      const g=document.createElement('p');g.className='g';g.textContent=m.glosses.join(' ');
      $('sent').prepend(g);$('sent').prepend(p);$('live').textContent='';
      if(speakOn&&'speechSynthesis' in window){const u=new SpeechSynthesisUtterance(m.text);u.lang='en-IN';
        speechSynthesis.cancel();speechSynthesis.speak(u);}}
    else if(m.type==='prompt'){const pr=$('prompt');pr.style.display=m.text?'block':'none';pr.textContent=m.text;}
    else if(m.type==='status'){$('status').textContent=m.text;}};
}
async function start(){
  if(stream) stream.getTracks().forEach(t=>t.stop());
  stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:facing,
    width:{ideal:640},height:{ideal:480},frameRate:{ideal:30}}});
  $('vid').srcObject=stream; $('vid').classList.toggle('mirror',facing==='user'); running=true; loop();
}
function loop(){
  if(!running) return;
  const v=$('vid');
  if(v.videoWidth && ws && ws.readyState===1 && inflight<2){
    const s=Math.min(1,480/Math.max(v.videoWidth,v.videoHeight)); canvas.width=v.videoWidth*s; canvas.height=v.videoHeight*s;
    ctx.drawImage(v,0,0,canvas.width,canvas.height);
    canvas.toBlob(b=>{ if(!b) return; b.arrayBuffer().then(buf=>{
      const head=new ArrayBuffer(8); new DataView(head).setFloat64(0,performance.now(),true);
      const msg=new Uint8Array(8+buf.byteLength); msg.set(new Uint8Array(head),0); msg.set(new Uint8Array(buf),8);
      ws.send(msg); inflight++; sent++;});},'image/jpeg',0.75);
  }
  const dt=(performance.now()-t0)/1000;
  if(dt>2){$('status').textContent=`streaming ${(sent/dt).toFixed(0)} fps · ${lat.toFixed(0)} ms round trip`;sent=0;t0=performance.now();}
  setTimeout(loop, 33);
}
$('go').onclick=()=>{running=!running;$('go').classList.toggle('on',running);$('go').textContent=running?'Start':'Paused';if(running)loop();};
$('flip').onclick=()=>{facing=facing==='user'?'environment':'user';start();};
$('speak').onclick=()=>{speakOn=!speakOn;$('speak').classList.toggle('on',speakOn);$('speak').textContent='Speak: '+(speakOn?'on':'off');};
$('clear').onclick=()=>{$('sent').innerHTML='';};
connect();
</script></body></html>"""


def lan_ips():
    """All IPv4 addresses of this laptop, the one used for the network/internet (Wi-Fi) FIRST.
    Virtual adapters (VirtualBox 192.168.56.x, VMware, WSL, Docker) are listed after it."""
    main = None
    for probe in ("8.8.8.8", "10.255.255.255"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((probe, 1))
            main = s.getsockname()[0]
            s.close()
            break
        except OSError:
            pass
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    ips.discard("127.0.0.1")
    ips.discard(main)
    out = ([main] if main and main != "127.0.0.1" else []) + sorted(ips)
    return out or ["127.0.0.1"]


def make_cert(ips):
    """Self-signed certificate for the laptop's LAN addresses (phones only allow the camera over HTTPS)."""
    os.makedirs(CERT_DIR, exist_ok=True)
    crt, key = os.path.join(CERT_DIR, "cert.pem"), os.path.join(CERT_DIR, "key.pem")
    marker = os.path.join(CERT_DIR, "ips.txt")
    if os.path.exists(crt) and os.path.exists(marker) and open(marker).read() == ",".join(ips):
        return crt, key
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    k = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "vanitra.local")])
    san = [x509.DNSName("localhost")] + [x509.IPAddress(ipaddress.ip_address(i)) for i in ips + ["127.0.0.1"]]
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(k.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=825))
            .add_extension(x509.SubjectAlternativeName(san), critical=False).sign(k, hashes.SHA256()))
    with open(crt, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key, "wb") as f:
        f.write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()))
    with open(marker, "w") as f:
        f.write(",".join(ips))
    return crt, key


class PhoneBridge:
    """Background server. frames() yields (bgr image, t seconds); send(dict) pushes JSON to every phone."""

    def __init__(self, port=8443, host="0.0.0.0", max_queue=2):
        self.port, self.host = port, host
        self.q = queue.Queue(maxsize=max_queue)
        self.clients = set()
        self.loop = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.ready.wait(10)

    def _run(self):
        from aiohttp import WSMsgType, web
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def index(_req):
            return web.Response(text=PAGE, content_type="text/html")

        async def ws_handler(req):
            ws = web.WebSocketResponse(max_msg_size=8 * 1024 * 1024)
            await ws.prepare(req)
            self.clients.add(ws)
            try:
                async for msg in ws:
                    if msg.type == WSMsgType.BINARY and len(msg.data) > 8:
                        (t_client,) = struct.unpack("<d", msg.data[:8])
                        try:
                            self.q.put_nowait((msg.data[8:], time.time()))
                        except queue.Full:                        # keep latency low: drop the oldest
                            try:
                                self.q.get_nowait()
                            except queue.Empty:
                                pass
                            self.q.put_nowait((msg.data[8:], time.time()))
                        await ws.send_str(json.dumps({"type": "ack", "t": t_client}))
            finally:
                self.clients.discard(ws)
            return ws

        app = web.Application(client_max_size=8 * 1024 * 1024)
        app.router.add_get("/", index)
        app.router.add_get("/ws", ws_handler)
        ips = lan_ips()
        crt, key = make_cert(ips)
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(crt, key)
        runner = web.AppRunner(app, access_log=None)
        self.loop.run_until_complete(runner.setup())
        self.loop.run_until_complete(web.TCPSite(runner, self.host, self.port, ssl_context=ctx).start())
        print("\n  Phone camera: on the phone (same Wi-Fi / hotspot) open")
        print(f"      https://{ips[0]}:{self.port}      <-- use this one (your Wi-Fi address)")
        for ip in ips[1:]:
            print(f"      https://{ip}:{self.port}      (other adapter: VirtualBox / VPN / hotspot - usually not reachable)")
        print("  The browser warns about the certificate once: tap Advanced -> Proceed. Allow the camera.\n")
        self.urls = [f"https://{ip}:{self.port}" for ip in ips]
        self.ready.set()
        self.loop.run_forever()

    def frames(self):
        import cv2
        while True:
            jpg, t = self.q.get()
            img = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                yield img, t

    def send(self, msg):
        if not self.loop or not self.clients:
            return
        data = json.dumps(msg)

        async def _send():
            for ws in list(self.clients):
                try:
                    await ws.send_str(data)
                except Exception:  # noqa: BLE001 - a phone that went away
                    self.clients.discard(ws)
        asyncio.run_coroutine_threadsafe(_send(), self.loop)


if __name__ == "__main__":
    b = PhoneBridge()
    n, t0 = 0, time.time()
    for img, _t in b.frames():
        n += 1
        if time.time() - t0 > 2:
            print(f"{n / (time.time() - t0):.1f} fps, {img.shape[1]}x{img.shape[0]}")
            b.send({"type": "status", "text": f"laptop receives {n / (time.time() - t0):.0f} fps"})
            n, t0 = 0, time.time()
