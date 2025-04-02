
from datetime import datetime, timedelta
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from config import db_config 
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import requests

# 🔑 Токен и chat_id
TELEGRAM_TOKEN = '7640038018:AAExF5BIk3SxURjAtJZAVXj28v5kHUWkxCs'
TELEGRAM_CHAT_ID = '745136500'

def wyslij_telegram_wiadomosc(tresc):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": tresc
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("❌ Błąd przy wysyłaniu Telegram:", e)
def wyslij_telegram_zamowienie(order_id, name, address, total_kwota, items):
    produkty_tekst = "\n".join([
        f"- {item['nazwa']} x {item['ilosc_zamowiona']} ({item['cena']} PLN/szt)" for item in items
    ])

    tresc = (
        f"🛒 Nowe zamówienie!\n"
        f"📦 ID: {order_id}\n"
        f"👤 Klient: {name}\n"
        f"🏠 Adres: {address}\n"
        f"🧺 Produkty:\n{produkty_tekst}\n"
        f"💰 Suma: {total_kwota:.2f} PLN"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": tresc
    }

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("❌ Błąd przy wysyłaniu Telegram:", e)

app = Flask(__name__)
app.secret_key = 'tajny_klucz'
def zapisz_log(akcja):
    if session.get('rola') != 'admin':
        return
    admin_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logi_admina (admin_id, akcja) VALUES (%s, %s)", (admin_id, akcja))
    conn.commit()
    cursor.close()
    conn.close()

def get_db():
    return mysql.connector.connect(**db_config)

# 🌍 Język
@app.before_request
def set_language():
    if 'lang' not in session:
        session['lang'] = 'pl'

@app.route('/change_lang/<lang>')
def change_lang(lang):
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

# 🏠 Strona główna
@app.route('/')
def index():
    lang = session.get('lang', 'pl')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 🛡️ Защита: если таблицы kategorii нет — не падаем
    try:
        cursor.execute("SELECT * FROM kategorie")
        kategorie = cursor.fetchall()
    except:
        kategorie = []

    # Фильтры из формы
    search = request.args.get('szukaj')
    sortuj = request.args.get('sortuj')
    kategoria = request.args.get('kategoria')

    # Базовый SQL
    query = "SELECT * FROM produkty WHERE 1=1"
    params = []

    # 🔎 Поиск по имени и opisie
    if search:
        query += " AND (nazwa LIKE %s OR opis LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])

    # 🧩 Фильтр по kategorii
    if kategoria:
        query += " AND id_kategorii = %s"
        params.append(kategoria)

    # 🔃 Сортировка
    if sortuj == 'nazwa':
        query += " ORDER BY nazwa"
    elif sortuj == 'cena_asc':
        query += " ORDER BY cena ASC"
    elif sortuj == 'cena_desc':
        query += " ORDER BY cena DESC"
    elif sortuj == 'najnowsze':
        query += " ORDER BY data_dodania DESC"
    else:
        query += " ORDER BY popularnosc DESC"

    try:
        cursor.execute(query, params)
        produkty = cursor.fetchall()
    except:
        produkty = []

    cursor.close()
    conn.close()

    return render_template("index.html", produkty=produkty, kategorie=kategorie, lang=lang)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    produkt_id = int(request.form['produkt_id'])
    ilosc = float(request.form['ilosc'])

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produkty WHERE id = %s", (produkt_id,))
    produkt = cursor.fetchone()
    cursor.close()
    conn.close()

    if not produkt:
        flash("Produkt nie istnieje.")
        return redirect(url_for('index'))

    # 🔧 Decimal to float
    from decimal import Decimal
    for key in produkt:
        if isinstance(produkt[key], Decimal):
            produkt[key] = float(produkt[key])

    produkt['ilosc_zamowiona'] = ilosc
    produkt['suma'] = round(float(produkt['cena']) * ilosc, 2)

    if 'cart' not in session:
        session['cart'] = []

    session['cart'].append(produkt)
    zapisz_log(f'Dodano do koszyka: {produkt["nazwa"]} ({ilosc})')

    session.modified = True
    flash("Dodano do koszyka.")
    return redirect(request.referrer or url_for('index'))


@app.route('/cart')
def cart():
    try:
        cart = session.get('cart', [])
        znizka = session.get('znizka', 0)
        total = sum(item['suma'] for item in cart)
        final_total = total * (1 - znizka / 100) if znizka else total
    except:
        cart = []
        znizka = 0
        total = 0
        final_total = 0

    # ✅ Получаем рекомендации по популярности (ТОП-3)
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM produkty ORDER BY popularnosc DESC LIMIT 3")
    rekomendacje = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'cart.html',
        cart=cart,
        total=round(total, 2),
        final_total=round(final_total, 2),
        znizka=znizka,
        rekomendacje=rekomendacje,
        lang=session.get('lang', 'pl')
    )


@app.route('/remove_from_cart/<int:index>')
def remove_from_cart(index):
    if 'cart' in session and 0 <= index < len(session['cart']):
        session['cart'].pop(index)
        zapisz_log(f'Usunięto z koszyka indeks {index}')

        session.modified = True
        flash("Usunięto z koszyka.")
    return redirect(url_for('cart'))
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        if 'user_id' not in session:
            flash("Zaloguj się najpierw.")
            return redirect(url_for('login'))

        try:
            name = request.form.get('name')
            email = request.form.get('email')
            address = request.form.get('address')

            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO orders (klient_id, data, imie, email, adres)
                VALUES (%s, %s, %s, %s, %s)
            """, (session['user_id'], datetime.now(), name, email, address))
            order_id = cursor.lastrowid
            zapisz_log(f'Złożono zamówienie ID {order_id}')

            cart_items = session.get('cart', [])
            for item in cart_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, produkt_id, ilosc, cena_jednostkowa)
                    VALUES (%s, %s, %s, %s)
                """, (order_id, item['id'], item['ilosc_zamowiona'], item['cena']))

                cursor.execute("""
                    UPDATE produkty
                    SET ilosc = ilosc - %s,
                        popularnosc = popularnosc + 1
                    WHERE id = %s
                """, (item['ilosc_zamowiona'], item['id']))

            conn.commit()
            cursor.close()
            conn.close()

            # ✅ Telegram уведомление с товарами
            total_kwota = sum(item['ilosc_zamowiona'] * item['cena'] for item in cart_items)
            produkty_tekst = "\n".join([
                f"- {item['nazwa']} x {item['ilosc_zamowiona']} ({item['cena']} PLN/szt)"
                for item in cart_items
            ])
            msg = (
                f"🛒 Nowe zamówienie #{order_id}\n"
                f"👤 Imię: {name}\n"
                f"📍 Adres: {address}\n"
                f"🧺 Produkty:\n{produkty_tekst}\n"
                f"💸 Suma: {total_kwota:.2f} PLN"
            )
            wyslij_telegram_wiadomosc(msg)

            session.pop('cart', None)
            session.pop('znizka', None)
            session['last_order_id'] = order_id
            flash("Zamówienie złożone!")

            return redirect(url_for('thank_you'))

        except Exception as e:
            print("❌ Błąd checkout:", e)
            flash("Wystąpił błąd podczas składania zamówienia.")
            return redirect(url_for('cart'))

    return render_template('checkout.html')



@app.route('/thank_you')
def thank_you():
    if 'last_order_id' not in session:
        return redirect(url_for('index'))

    now = datetime.now()
    return render_template('thank_you.html', now=now)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        imie = request.form['imie']
        email = request.form['email']
        haslo = generate_password_hash(request.form['haslo'])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO uzytkownicy (imie, email, haslo, rola)
            VALUES (%s, %s, %s, %s)
        """, (imie, email, haslo, 'klient'))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Rejestracja zakończona sukcesem.")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        haslo = request.form['haslo']

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM uzytkownicy WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['haslo'], haslo):
            session['user_id'] = user['id']
            session['rola'] = user['rola']
            session['user_name'] = user['imie']
            flash("Zalogowano pomyślnie.")
            return redirect(url_for('index'))
        else:
            flash("Błędny email lub hasło.")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Wylogowano.")
    return redirect(url_for('index'))
@app.route('/product/<int:id>')
def product(id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM produkty WHERE id = %s", (id,))
        produkt = cursor.fetchone()

        if not produkt:
            flash("Produkt nie istnieje.")
            return redirect(url_for('index'))

        cursor.execute("SELECT AVG(ocena) as srednia FROM oceny WHERE produkt_id = %s", (id,))
        rating = cursor.fetchone()['srednia']

        cursor.execute("""
            SELECT k.tresc, u.imie, k.data
            FROM komentarze k
            JOIN uzytkownicy u ON k.uzytkownik_id = u.id
            WHERE produkt_id = %s
            ORDER BY k.data DESC
        """, (id,))
        komentarze = cursor.fetchall()

    except:
        produkt = None
        rating = None
        komentarze = []

    cursor.close()
    conn.close()

    return render_template('product.html', produkt=produkt, rating=rating, komentarze=komentarze)


@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        flash("Zaloguj się, aby ocenić.")
        return redirect(url_for('login'))

    produkt_id = int(request.form['produkt_id'])
    ocena = int(request.form['ocena'])

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO oceny (produkt_id, uzytkownik_id, ocena)
        VALUES (%s, %s, %s)
    """, (produkt_id, session['user_id'], ocena))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Dziękujemy za ocenę!")
    return redirect(url_for('product', id=produkt_id))


@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        flash("Zaloguj się, aby dodać komentarz.")
        return redirect(url_for('login'))

    produkt_id = int(request.form['produkt_id'])
    tresc = request.form['tresc']

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO komentarze (produkt_id, uzytkownik_id, tresc)
        VALUES (%s, %s, %s)
    """, (produkt_id, session['user_id'], tresc))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Komentarz dodany!")
    return redirect(url_for('product', id=produkt_id))



@app.route('/history')
def history():
    if 'user_id' not in session:
        flash("Zaloguj się, aby zobaczyć historię.")
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.id, o.data, p.nazwa, oi.ilosc, oi.cena_jednostkowa
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN produkty p ON oi.produkt_id = p.id
        WHERE o.klient_id = %s
        ORDER BY o.data DESC
    """, (session['user_id'],))
    historia = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('history.html', historia=historia)
@app.route('/admin')
def admin():
    if session.get('rola') != 'admin':
        flash("Brak dostępu.")
        return redirect(url_for('index'))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # 📦 Wszystkie produkty
    cursor.execute("SELECT * FROM produkty ORDER BY popularnosc DESC")
    produkty = cursor.fetchall()

    # 🔝 Najpopularniejsze produkty
    cursor.execute("SELECT nazwa, popularnosc FROM produkty ORDER BY popularnosc DESC LIMIT 5")
    top5 = cursor.fetchall()

    # 💤 Najmniej popularne
    cursor.execute("SELECT nazwa, popularnosc FROM produkty ORDER BY popularnosc ASC LIMIT 5")
    worst5 = cursor.fetchall()

    # 💰 Średnia wartość zamówień
    cursor.execute("SELECT ROUND(AVG(ilosc * cena_jednostkowa), 2) as avg_value FROM order_items")
    avg_order = cursor.fetchone()['avg_value']

    # 👥 Najaktywniejsi klienci
    cursor.execute("""
        SELECT u.imie, COUNT(o.id) AS liczba
        FROM uzytkownicy u
        JOIN orders o ON u.id = o.klient_id
        GROUP BY u.id
        ORDER BY liczba DESC
        LIMIT 5
    """)
    top_klienci = cursor.fetchall()

    # 📊 Wykres - suma sprzedaży z ostatnich 7 dni
    cursor.execute("""
        SELECT DATE(o.data) AS dzien, ROUND(SUM(oi.ilosc * oi.cena_jednostkowa), 2) AS suma
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.data >= CURDATE() - INTERVAL 7 DAY
        GROUP BY dzien
        ORDER BY dzien
    """)
    sprzedaz_dniowa = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin_dashboard.html',
        produkty=produkty,
        top5=top5,
        worst5=worst5,
        avg_order=avg_order,
        top_klienci=top_klienci,
        sprzedaz_dniowa=sprzedaz_dniowa,
        lang=session.get('lang', 'pl')
    )

import csv
from io import StringIO
from flask import Response

@app.route('/admin/export/produkty')
def export_produkty():
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nazwa, cena, ilosc, popularnosc FROM produkty")
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID', 'Nazwa', 'Cena', 'Ilość', 'Popularność'])
    writer.writerows(rows)

    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=produkty.csv'})


@app.route('/admin/export/zamowienia')
def export_zamowienia():
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT o.id, o.data, u.imie, p.nazwa, oi.ilosc, oi.cena_jednostkowa
        FROM orders o
        JOIN uzytkownicy u ON o.klient_id = u.id
        JOIN order_items oi ON o.id = oi.order_id
        JOIN produkty p ON oi.produkt_id = p.id
    """)
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['ID zamówienia', 'Data', 'Klient', 'Produkt', 'Ilość', 'Cena'])
    writer.writerows(rows)

    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=zamowienia.csv'})


@app.route('/admin/export/klienci')
def export_klienci():
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.imie, u.email, COUNT(o.id) AS liczba_zamowien
        FROM uzytkownicy u
        LEFT JOIN orders o ON u.id = o.klient_id
        WHERE u.rola = 'klient'
        GROUP BY u.id
    """)
    rows = cursor.fetchall()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Imię', 'Email', 'Liczba zamówień'])
    writer.writerows(rows)

    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=klienci.csv'})
@app.route('/admin/users')
def admin_users():
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.id, u.imie, u.email, u.rola, COUNT(o.id) AS zamowien
        FROM uzytkownicy u
        LEFT JOIN orders o ON u.id = o.klient_id
        GROUP BY u.id
    """)
    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_users.html', users=users, lang=session.get('lang', 'pl'))


@app.route('/admin/users/role/<int:user_id>')
def change_user_role(user_id):
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT rola FROM uzytkownicy WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        flash("Użytkownik nie istnieje.")
        return redirect(url_for('admin_users'))

    new_role = 'admin' if user['rola'] == 'klient' else 'klient'
    cursor.execute("UPDATE uzytkownicy SET rola = %s WHERE id = %s", (new_role, user_id))
    conn.commit()

    cursor.close()
    conn.close()
    zapisz_log(f'Zmieniono rolę użytkownika ID {user_id} na {new_role}')

    flash(f"Zmieniono rolę użytkownika na: {new_role}")
    return redirect(url_for('admin_users'))
@app.route('/apply_promo', methods=['POST'])
def apply_promo():
    kod = request.form.get('kod')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT znizka FROM promokody WHERE kod = %s AND aktywny = TRUE", (kod,))
    promo = cursor.fetchone()
    cursor.close()
    conn.close()

    if promo:
        session['znizka'] = promo['znizka']
        zapisz_log(f'Zastosowano kod promocyjny: {kod}')

        flash(f"Zastosowano kod: {kod} (-{promo['znizka']}%)")
    else:
        flash("Nieprawidłowy lub nieaktywny kod rabatowy.")

    return redirect(url_for('cart'))

@app.route('/admin/promokody')
def admin_promokody():
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM promokody ORDER BY id DESC")
    promokody = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin_promos.html', promokody=promokody, lang=session.get('lang', 'pl'))


@app.route('/admin/promokody/add', methods=['POST'])
def add_promokod():
    if session.get('rola') != 'admin':
        abort(403)

    kod = request.form.get('kod')
    znizka = request.form.get('znizka')

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO promokody (kod, znizka, aktywny) VALUES (%s, %s, TRUE)", (kod, znizka))
        conn.commit()
        flash("Dodano nowy kod promocyjny.")
    except:
        flash("Błąd: kod może już istnieje lub jest nieprawidłowy.")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin_promokody'))


@app.route('/admin/promokody/toggle/<int:id>')
def toggle_promokod(id):
    if session.get('rola') != 'admin':
        abort(403)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE promokody SET aktywny = NOT aktywny WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Zmieniono status kodu.")
    return redirect(url_for('admin_promokody'))

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    session.modified = True
    flash("Koszyk został wyczyszczony." if session.get('lang') == 'pl' else "Cart cleared.")
    return redirect(url_for('cart'))

# 🧠 Admin-only future: Add/Edit/Delete products (optional)
# Można dodać więcej metod tutaj, jeśli chcesz CRUD panel admina.

# ✅ Flask start
if __name__ == '__main__':
    app.run(debug=True)

