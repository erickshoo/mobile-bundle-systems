"""
Mfumo wa Vifurushi vya Simu (Mobile Bundles System)
Console app using Python + SQLite. Hakuna library ya ziada inayohitajika.
Run: python vifurushi_system.py
"""
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "vifurushi.db"
ADMIN_PIN = "1234"


# ---------- DATABASE ----------
def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        balance INTEGER DEFAULT 0)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS bundles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        data_mb INTEGER,
        minutes INTEGER,
        sms INTEGER,
        price INTEGER NOT NULL,
        days INTEGER NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        bundle_name TEXT,
        data_left INTEGER,
        minutes_left INTEGER,
        sms_left INTEGER,
        bought_on TEXT,
        expires_on TEXT)""")

    # Weka vifurushi vya mwanzo kama hakuna
    cur.execute("SELECT COUNT(*) FROM bundles")
    if cur.fetchone()[0] == 0:
        starter = [
            ("Daily Mini",    200,   10,  20, 1000,  1),
            ("Daily Plus",    700,   30,  50, 2000,  1),
            ("Weekly Smart", 3000,  100, 150, 5000,  7),
            ("Monthly Pro", 15000,  500, 500, 20000, 30),
        ]
        cur.executemany(
            "INSERT INTO bundles (name, data_mb, minutes, sms, price, days) "
            "VALUES (?, ?, ?, ?, ?, ?)", starter)
    conn.commit()
    conn.close()


# ---------- HELPERS ----------
def line():
    print("-" * 60)


def ask_int(message):
    while True:
        value = input(message).strip()
        if value.isdigit():
            return int(value)
        print("Tafadhali weka namba sahihi.")


def get_user(phone):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    return user


# ---------- BUNDLES ----------
def show_bundles():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM bundles ORDER BY price").fetchall()
    conn.close()
    line()
    print(f"{'ID':<4}{'Jina':<15}{'Data':<10}{'Dak':<7}{'SMS':<7}{'Bei':<9}{'Siku'}")
    line()
    for b in rows:
        print(f"{b['id']:<4}{b['name']:<15}{str(b['data_mb']) + 'MB':<10}"
              f"{b['minutes']:<7}{b['sms']:<7}{b['price']:<9}{b['days']}")
    line()


def add_bundle():
    pin = input("Weka PIN ya admin: ").strip()
    if pin != ADMIN_PIN:
        print("PIN si sahihi.")
        return
    name = input("Jina la kifurushi: ").strip()
    data_mb = ask_int("Data (MB): ")
    minutes = ask_int("Dakika: ")
    sms = ask_int("SMS: ")
    price = ask_int("Bei (TZS): ")
    days = ask_int("Siku za kudumu: ")
    conn = get_conn()
    conn.execute(
        "INSERT INTO bundles (name, data_mb, minutes, sms, price, days) "
        "VALUES (?, ?, ?, ?, ?, ?)", (name, data_mb, minutes, sms, price, days))
    conn.commit()
    conn.close()
    print("Kifurushi kimeongezwa.")


# ---------- USER ACTIONS ----------
def register():
    phone = input("Namba ya simu (mf. 0712345678): ").strip()
    if not (phone.isdigit() and len(phone) == 10):
        print("Namba lazima iwe na tarakimu 10.")
        return
    if get_user(phone):
        print("Namba hii tayari imesajiliwa.")
        return
    name = input("Jina lako: ").strip()
    conn = get_conn()
    conn.execute("INSERT INTO users (phone, name, balance) VALUES (?, ?, 0)",
                 (phone, name))
    conn.commit()
    conn.close()
    print(f"Karibu {name}! Akaunti imeundwa.")


def deposit(phone):
    amount = ask_int("Kiasi cha kuweka (TZS): ")
    if amount <= 0:
        print("Kiasi lazima kiwe zaidi ya 0.")
        return
    conn = get_conn()
    conn.execute("UPDATE users SET balance = balance + ? WHERE phone = ?",
                 (amount, phone))
    conn.commit()
    conn.close()
    print(f"Umeweka TZS {amount}. Salio jipya: TZS {get_user(phone)['balance']}")


def buy_bundle(phone):
    show_bundles()
    bundle_id = ask_int("Weka ID ya kifurushi unachotaka: ")
    conn = get_conn()
    bundle = conn.execute("SELECT * FROM bundles WHERE id = ?", (bundle_id,)).fetchone()
    if not bundle:
        print("Kifurushi hakipo.")
        conn.close()
        return
    user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
    if user["balance"] < bundle["price"]:
        print(f"Salio halitoshi. Unahitaji TZS {bundle['price']}, "
              f"una TZS {user['balance']}.")
        conn.close()
        return

    now = datetime.now()
    expires = now + timedelta(days=bundle["days"])
    conn.execute("UPDATE users SET balance = balance - ? WHERE phone = ?",
                 (bundle["price"], phone))
    conn.execute(
        "INSERT INTO purchases (phone, bundle_name, data_left, minutes_left, "
        "sms_left, bought_on, expires_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (phone, bundle["name"], bundle["data_mb"], bundle["minutes"],
         bundle["sms"], now.strftime("%Y-%m-%d %H:%M"),
         expires.strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    print(f"Umenunua {bundle['name']} kwa TZS {bundle['price']}. "
          f"Kinaisha: {expires.strftime('%Y-%m-%d %H:%M')}")


def active_purchases(phone):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM purchases WHERE phone = ? AND expires_on > ? "
        "ORDER BY id", (phone, now)).fetchall()
    conn.close()
    return rows


def my_bundles(phone):
    rows = active_purchases(phone)
    if not rows:
        print("Huna kifurushi kinachofanya kazi.")
        return
    line()
    for r in rows:
        print(f"[{r['id']}] {r['bundle_name']}")
        print(f"    Data: {r['data_left']}MB | Dakika: {r['minutes_left']} | "
              f"SMS: {r['sms_left']}")
        print(f"    Kinaisha: {r['expires_on']}")
    line()


def use_service(phone):
    """Simulation: tumia data, dakika au SMS kutoka kwenye kifurushi."""
    rows = active_purchases(phone)
    if not rows:
        print("Huna kifurushi kinachofanya kazi. Nunua kwanza.")
        return
    my_bundles(phone)
    pid = ask_int("Weka ID ya kifurushi cha kutumia: ")
    print("1. Tumia Data (MB)\n2. Piga simu (dakika)\n3. Tuma SMS")
    choice = input("Chagua: ").strip()
    columns = {"1": "data_left", "2": "minutes_left", "3": "sms_left"}
    if choice not in columns:
        print("Chaguo si sahihi.")
        return
    column = columns[choice]
    amount = ask_int("Kiasi cha kutumia: ")

    conn = get_conn()
    row = conn.execute("SELECT * FROM purchases WHERE id = ? AND phone = ?",
                       (pid, phone)).fetchone()
    if not row or row["id"] not in [r["id"] for r in rows]:
        print("Kifurushi hakipo au kimeisha muda.")
    elif row[column] < amount:
        print(f"Kimebaki {row[column]} tu. Haitoshi.")
    else:
        # column inatoka kwenye dictionary yetu, si kwa mtumiaji, hivyo ni salama
        conn.execute(f"UPDATE purchases SET {column} = {column} - ? WHERE id = ?",
                     (amount, pid))
        conn.commit()
        print(f"Umetumia {amount}. Kimebaki {row[column] - amount}.")
    conn.close()


def history(phone):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM purchases WHERE phone = ? ORDER BY id DESC",
                        (phone,)).fetchall()
    conn.close()
    if not rows:
        print("Hujawahi kununua kifurushi.")
        return
    line()
    for r in rows:
        print(f"{r['bought_on']}  {r['bundle_name']}")
    line()


# ---------- MENUS ----------
def user_menu(phone):
    while True:
        user = get_user(phone)
        print(f"\n=== {user['name']} ({phone}) | Salio: TZS {user['balance']} ===")
        print("1. Angalia vifurushi")
        print("2. Weka pesa")
        print("3. Nunua kifurushi")
        print("4. Vifurushi vyangu")
        print("5. Tumia huduma")
        print("6. Historia ya manunuzi")
        print("0. Toka")
        choice = input("Chagua: ").strip()
        if choice == "1":
            show_bundles()
        elif choice == "2":
            deposit(phone)
        elif choice == "3":
            buy_bundle(phone)
        elif choice == "4":
            my_bundles(phone)
        elif choice == "5":
            use_service(phone)
        elif choice == "6":
            history(phone)
        elif choice == "0":
            print("Kwa heri!")
            break
        else:
            print("Chaguo si sahihi.")


def main():
    setup_database()
    while True:
        print("\n===== MFUMO WA VIFURUSHI VYA SIMU =====")
        print("1. Jisajili")
        print("2. Ingia")
        print("3. Admin: Ongeza kifurushi")
        print("0. Funga programu")
        choice = input("Chagua: ").strip()
        if choice == "1":
            register()
        elif choice == "2":
            phone = input("Namba ya simu: ").strip()
            if get_user(phone):
                user_menu(phone)
            else:
                print("Namba haijasajiliwa.")
        elif choice == "3":
            add_bundle()
        elif choice == "0":
            print("Programu imefungwa.")
            break
        else:
            print("Chaguo si sahihi.")


if __name__ == "__main__":
    main()
