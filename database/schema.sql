DROP DATABASE IF EXISTS grocery_shop;
CREATE DATABASE grocery_shop CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE grocery_shop;

-- 👤 Użytkownicy
CREATE TABLE uzytkownicy (
    id INT AUTO_INCREMENT PRIMARY KEY,
    imie VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    haslo TEXT NOT NULL,
    rola ENUM('klient', 'admin') DEFAULT 'klient'
);

-- 🏷 Kategorie
CREATE TABLE kategorie (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nazwa VARCHAR(100) NOT NULL
);

-- 📦 Produkty
CREATE TABLE produkty (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nazwa VARCHAR(100) NOT NULL,
    opis TEXT,
    cena DECIMAL(10,2) NOT NULL,
    ilosc DECIMAL(10,2) DEFAULT 0,
    typ_ceny ENUM('szt', 'kg') DEFAULT 'szt',
    zdjecie VARCHAR(100),
    data_dodania DATETIME DEFAULT CURRENT_TIMESTAMP,
    popularnosc INT DEFAULT 0,
    id_kategorii INT,
    FOREIGN KEY (id_kategorii) REFERENCES kategorie(id) ON DELETE SET NULL
);

-- 🧾 Zamówienia
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    klient_id INT,
    data DATETIME DEFAULT CURRENT_TIMESTAMP,
    imie VARCHAR(100),
    email VARCHAR(100),
    adres TEXT,
    FOREIGN KEY (klient_id) REFERENCES uzytkownicy(id)
);

-- 🛒 Pozycje zamówień
CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    produkt_id INT,
    ilosc DECIMAL(10,2),
    cena_jednostkowa DECIMAL(10,2),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (produkt_id) REFERENCES produkty(id) ON DELETE SET NULL
);

-- ⭐ Oceny
CREATE TABLE oceny (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produkt_id INT,
    uzytkownik_id INT,
    ocena INT CHECK (ocena BETWEEN 1 AND 5),
    FOREIGN KEY (produkt_id) REFERENCES produkty(id) ON DELETE CASCADE,
    FOREIGN KEY (uzytkownik_id) REFERENCES uzytkownicy(id) ON DELETE CASCADE
);

-- 💬 Komentarze
CREATE TABLE komentarze (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produkt_id INT,
    uzytkownik_id INT,
    tresc TEXT,
    data DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (produkt_id) REFERENCES produkty(id) ON DELETE CASCADE,
    FOREIGN KEY (uzytkownik_id) REFERENCES uzytkownicy(id) ON DELETE CASCADE
);

-- 🎁 Promokody
CREATE TABLE promokody (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kod VARCHAR(50) UNIQUE NOT NULL,
    znizka INT CHECK (znizka BETWEEN 1 AND 100),
    aktywny BOOLEAN DEFAULT TRUE
);

-- 🧠 Logi admina
CREATE TABLE logi_admina (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT,
    akcja TEXT,
    czas TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES uzytkownicy(id) ON DELETE CASCADE
);
