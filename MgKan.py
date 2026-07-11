#!/usr/bin/env python3
import os, sys, json, time, hashlib, subprocess

DB_FILE = "mgkan_keys.json"

def load_db():
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"keys": {}, "used": []}

def validate_key(key):
    db = load_db()
    key = key.upper()
    if key not in db["keys"]:
        return False, "❌ Invalid key"
    if int(time.time()) > db["keys"][key]["expiry"]:
        return False, "❌ Key expired"
    if key in db.get("used", []):
        return False, "❌ Key already used"
    return True, "✅ Key valid"

def register_use(key):
    db = load_db()
    if "used" not in db:
        db["used"] = []
    db["used"].append(key)
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def main():
    print("\n🔥 MGKAN TOOL - Ruijie Scanner\n")
    if not os.path.exists("mgkan_key.txt"):
        key = input("🔑 Enter your key: ").strip()
        with open("mgkan_key.txt", "w") as f:
            f.write(key)
    else:
        with open("mgkan_key.txt", "r") as f:
            key = f.read().strip()
    
    valid, msg = validate_key(key)
    if not valid:
        print(msg)
        sys.exit(1)
    
    register_use(key)
    print("✅ Access granted! Launching...\n")
    os.system("python3 scanner.py")

if __name__ == "__main__":
    main()
