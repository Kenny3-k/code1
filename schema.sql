CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    loyalty_points INTEGER DEFAULT 0
);

CREATE TABLE zoo_bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    visit_date TEXT,
    tickets INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE hotel_bookings(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    check_in TEXT,
    check_out TEXT,
    room_type TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);