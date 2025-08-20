from datetime import datetime, timedelta, date
import xml.etree.ElementTree as ET
import requests
import os
import json
import sqlite3


#                         ---------------------------- db ----------------------------

# init db by create table history_save in sqlite
def db_init():
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS history_save
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       data_created
                       TEXT,
                       cash
                       REAL,
                       to_value
                       TEXT,
                       for_value
                       TEXT,
                       result
                       REAL
                   )
                   ''')

    conn.commit()
    conn.close()


# search in table by some params
def search_history(date=None, cash=None, to_value=None, for_value=None, result=None):
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    query = "SELECT id, data_created, cash,for_value,to_value,result FROM history_save WHERE 1=1"
    params = []
    if date:
        query += " AND data_created = ?"
        params.append(date)
    if cash:
        query += " AND cash = ?"
        params.append(cash)
    if to_value:
        query += " AND to_value = ?"
        params.append(to_value)
    if for_value:
        query += " AND for_value = ?"
        params.append(for_value)
    if result:
        query += " AND result = ?"
        params.append(result)
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return rows


# get all history in order for beauty show
def get_all_history():
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, data_created, cash,for_value,to_value,result FROM history_save")
    rows = cursor.fetchall()
    conn.close()
    return rows


# save operation in db
def save(date, for_value, to_value, cash, result):
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute('''
                   INSERT INTO history_save (data_created, for_value, to_value, cash, result)
                   VALUES (?, ?, ?, ?, ?)
                   ''', (date, for_value, to_value, cash, result))
    conn.commit()
    conn.close()


# delete all rows from table
def delete():
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM `history_save`')
    conn.commit()
    conn.close()


#                         ---------------------------- business ----------------------------

# convert values
def convert(to_value, for_value, cash, today_values):
    result = (cash * today_values[for_value]) / today_values[to_value]
    date_str = datetime.today().date().strftime("%d/%m/%Y")
    save(date_str, for_value, to_value, cash, result)
    return result


# get from cbrf values by day/month/year
def get_currency_rates(day, month, year):
    day = f"{day:02d}"
    month = f"{month:02d}"
    year = f"{year:02d}"

    url = f"http://www.cbr.ru/scripts/XML_daily.asp?date_req={day}/{month}/{year}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except (requests.RequestException, ValueError) as e:
        print(e)
        return None
    try:
        content = ET.fromstring(response.content)
        rates = {"EUR": 0.0, "USD": 0.0, "GBP": 0.0, "JPY": 0.0, "RUB": 1}
        for valute in content.findall('Valute'):
            char_code = valute.find('CharCode').text
            if char_code not in rates:
                continue
            value = valute.find('Value').text.replace(',', '.')
            nominal = int(valute.find('Nominal').text)
            rates[char_code] = round(float(value) / nominal, 4)
        return rates
    except (AttributeError, ET.ParseError) as e:
        print(e)
        return None


# get some days before today with delta=delay
def get_previous_dates(delay):
    today = datetime.now()
    one_month_ago = today - timedelta(days=delay)
    current_date = today
    data = []
    while current_date >= one_month_ago:
        data.append(current_date)
        current_date -= timedelta(days=1)
    return data


# update file rate.json from dates
def update_rates_file(file_path, dates, existing_data):
    updated_data = existing_data.copy()
    for date_obj in reversed(dates):
        date_str = date_obj.strftime('%d-%m-%Y')
        if date_str in updated_data and updated_data[date_str] is not None:
            continue
        rates = get_currency_rates(
            date_obj.day,
            date_obj.month,
            date_obj.year
        )
        if rates:
            updated_data[date_str] = rates
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving rates to {file_path}: {e}")


# supports current monthly dates in rate.json
def maintain_currency_rates(file_path: str = "rate.json"):
    existing_data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except (IOError, json.JSONDecodeError):
            existing_data = {}
    cutoff_date = date.today() - timedelta(days=31)
    updated_data = {
        date_str: rates for date_str, rates in existing_data.items()
        if datetime.strptime(date_str, '%d-%m-%Y').date() >= cutoff_date
    }
    existing_dates = {
        datetime.strptime(d, '%d-%m-%Y').date() for d in updated_data.keys()
    }
    all_dates = set(get_previous_dates(31))
    dates_to_fetch = sorted(all_dates - existing_dates)
    if dates_to_fetch:
        update_rates_file(file_path, dates_to_fetch, updated_data)
