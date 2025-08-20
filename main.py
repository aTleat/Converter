import tkinter as tk
from tkinter import ttk

from dateutil.utils import today
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from datetime import datetime, timedelta, date
import json
import matplotlib.dates as mdates
import service


# init db
def init_db():
    service.db_init()


# class of main app
class CurrencyConverterApp:
    def __init__(self, root):

        # some needed values

        self.user_email = None
        self.root = root
        self.root.title("Конвертер валют")
        self.root.geometry("800x600")

        # init some data before start(db,rate.json,today courses)

        init_db()
        service.maintain_currency_rates()
        self.today_values = service.get_currency_rates(datetime.today().date().day,
                                                       datetime.today().date().month,
                                                       datetime.today().date().year)
        if self.today_values is None:
            tk.messagebox.showinfo("Ошибка",
                                   "Отсутствует подключение к интернету.Будут использованы локальные значения")


        # notebook with 3 tabs(converter,history,chart)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill='both')
        self.create_converter_tab()
        self.create_history_tab()
        self.create_chart_tab()

    #                     -------------------- converter tab --------------------

    def create_converter_tab(self):
        # main

        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Конвертер")

        # fields with edit values

        ttk.Label(frame, text="Из:").grid(row=0, column=0, padx=10, pady=10)
        self.from_currency = ttk.Combobox(frame, values=["USD", "EUR", "RUB", "GBP", "JPY"])
        self.from_currency.grid(row=0, column=1, padx=10, pady=10)
        self.from_currency.set("USD")
        ttk.Label(frame, text="В:").grid(row=1, column=0, padx=10, pady=10)
        self.to_currency = ttk.Combobox(frame, values=["USD", "EUR", "RUB", "GBP", "JPY"])
        self.to_currency.grid(row=1, column=1, padx=10, pady=10)
        self.to_currency.set("RUB")
        ttk.Label(frame, text="Сумма:").grid(row=2, column=0, padx=10, pady=10)
        self.cash = ttk.Entry(frame)
        self.cash.grid(row=2, column=1, padx=10, pady=10)
        self.cash.insert(0, "1")

        # buttons for convert and send email

        convert_btn = ttk.Button(frame, text="Конвертировать", command=self.perform_conversion)
        convert_btn.grid(row=3, column=0, padx=5, pady=10, sticky='e')
        email_btn = ttk.Button(frame, text="Отправить результат", command=self.show_email_popup)
        email_btn.grid(row=3, column=1, padx=5, pady=10, sticky='w')
        self.result_label = ttk.Label(frame, text="", font=('Helvetica', 12, 'bold'))
        self.result_label.grid(row=4, column=0, columnspan=2, pady=10)
        self.user_email = None

    # send for email window on click button of send
    def show_email_popup(self):
        # check result for empty content

        if self.result_label.cget("text") == "":
            tk.messagebox.showinfo("Информация", "Сначала выполните конвертацию")
            return

        # window up

        popup = tk.Toplevel()
        popup.title("Отправить результат на email")
        popup.geometry("350x180")
        popup.resizable(False, False)
        popup.update_idletasks()
        width = popup.winfo_width()
        height = popup.winfo_height()
        x = (popup.winfo_screenwidth() // 2) - (width // 2)
        y = (popup.winfo_screenheight() // 2) - (height // 2)
        popup.geometry(f'+{x}+{y}')
        ttk.Label(popup, text="Введите email для отправки результата:").pack(pady=10)
        self.email_entry = ttk.Entry(popup, width=30)
        self.email_entry.pack(pady=5)

        # destroy this window if email correct and get email result window

        def submit_email():
            email = self.email_entry.get()
            if "@" in email and "." in email:
                self.user_email = email
                self.send_email_result()
                popup.destroy()
            else:
                tk.messagebox.showwarning("Неверный email", "Пожалуйста, введите корректный email")

        # buttons

        submit_btn = ttk.Button(popup, text="Отправить", command=submit_email)
        submit_btn.pack(pady=10)
        cancel_btn = ttk.Button(popup, text="Отмена", command=popup.destroy)
        cancel_btn.pack(pady=5)

    # show window with result and make illision of send email

    def send_email_result(self):
        if self.user_email and self.result_label:
            msg = (
                f"Результат конвертации:\n\n"
                f"{self.result_label.cget("text")}"
            )
            tk.messagebox.showinfo(
                "Успешно",
                f"Результат конвертации отправлен на {self.user_email}\n\n{msg}"
            )
        else:
            tk.messagebox.showwarning("Ошибка", "Нет данных для отправки")

    # convert values

    def perform_conversion(self):
        try:
            from_curr = self.from_currency.get()
            to_curr = self.to_currency.get()
            cash = float(self.cash.get())
            result = service.convert(to_curr, from_curr, cash, today_values=self.today_values)
            result_text = f"{cash:.2f} {from_curr} = {result:.2f} {to_curr}"
            self.result_label.config(text=result_text)
            self.update_history_table()
        except ValueError:
            self.result_label.config(text="Ошибка: введите корректную сумму")

    #                       -------------------- history tab --------------------

    def create_history_tab(self):
        # main

        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="История")

        # filters to find in db
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(pady=5, fill='x')
        ttk.Label(filter_frame, text="Дата:").pack(side='left', padx=5)
        self.filter_date = ttk.Entry(filter_frame, width=10)
        self.filter_date.pack(side='left', padx=5)
        ttk.Label(filter_frame, text="Из:").pack(side='left', padx=5)
        self.filter_from = ttk.Combobox(filter_frame, values=["", "USD", "EUR", "RUB", "GBP", "JPY"], width=5)
        self.filter_from.pack(side='left', padx=5)
        ttk.Label(filter_frame, text="В:").pack(side='left', padx=5)
        self.filter_to = ttk.Combobox(filter_frame, values=["", "USD", "EUR", "RUB", "GBP", "JPY"], width=5)
        self.filter_to.pack(side='left', padx=5)

        # buttons to do some with db

        filter_btn = ttk.Button(filter_frame, text="Фильтровать", command=self.apply_filters)
        filter_btn.pack(side='left', padx=5)
        reset_btn = ttk.Button(filter_frame, text="Сброс", command=self.reset_filters)
        reset_btn.pack(side='left', padx=5)
        delete_btn = ttk.Button(filter_frame, text="Удалить", command=self.delete_history)
        delete_btn.pack(side='left', padx=5)

        # columns setting for show
        columns = ("id", "date", "amount", "from", "to", "result")
        self.history_tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.history_tree.heading("id", text="ID")
        self.history_tree.heading("date", text="Дата")
        self.history_tree.heading("amount", text="Сумма")
        self.history_tree.heading("from", text="Из")
        self.history_tree.heading("to", text="В")
        self.history_tree.heading("result", text="Результат")
        self.history_tree.column("id", width=50, anchor='center')
        self.history_tree.column("date", width=100)
        self.history_tree.column("amount", width=100, anchor='e')
        self.history_tree.column("from", width=60, anchor='center')
        self.history_tree.column("to", width=60, anchor='center')
        self.history_tree.column("result", width=100, anchor='e')
        self.history_tree.pack(fill='both', expand=True, padx=10, pady=10)

        # update table

        self.update_history_table()

    # delete all rows

    def delete_history(self):
        service.delete()
        self.update_history_table()

    # apply filters get into db and update history

    def apply_filters(self):
        date_filter = self.filter_date.get() or None
        from_filter = self.filter_from.get() or None
        to_filter = self.filter_to.get() or None
        filtered_data = service.search_history(
            date=date_filter,
            for_value=from_filter,
            to_value=to_filter
        )
        self.update_history_table(filtered_data)

    # delete all filters

    def reset_filters(self):
        self.filter_date.delete(0, 'end')
        self.filter_from.set('')
        self.filter_to.set('')
        self.update_history_table()

    # destroy current table and draw new by data

    def update_history_table(self, data=None):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        if data is None:
            data = service.get_all_history()
        for row in data:
            self.history_tree.insert("", "end", values=row)

    #                            -------------------- chart tab --------------------
    def create_chart_tab(self):
        # main

        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="График")

        # valute and period select

        control_frame = ttk.Frame(frame)
        control_frame.pack(pady=5, fill='x')
        ttk.Label(control_frame, text="Валюта:").pack(side='left', padx=5)
        self.chart_currency = ttk.Combobox(control_frame, values=["USD", "EUR", "GBP", "JPY"], width=5)
        self.chart_currency.pack(side='left', padx=5)
        self.chart_currency.set("USD")
        ttk.Label(control_frame, text="Период (дней):").pack(side='left', padx=5)
        self.chart_period = ttk.Combobox(control_frame, values=[7, 14, 30], width=5)
        self.chart_period.pack(side='left', padx=5)
        self.chart_period.set(30)

        # button for create chart

        plot_btn = ttk.Button(control_frame, text="Построить график", command=self.plot_chart)
        plot_btn.pack(side='left', padx=5)
        self.chart_frame = ttk.Frame(frame)
        self.chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.plot_chart()

    # create chart

    def plot_chart(self):
        # chooses valute and period

        currency = self.chart_currency.get()
        period = int(self.chart_period.get())

        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # get data

        try:
            with open("rate.json", 'r', encoding='utf-8') as f:
                rates_data = json.load(f)
        except (IOError, json.JSONDecodeError):
            rates_data = {}
        if not rates_data:
            ttk.Label(self.chart_frame, text="Нет данных для построения графика").pack(expand=True)
            return

        # prepare data for chart

        chart_data = []
        for date_str, currencies in rates_data.items():
            try:
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                if currency in currencies:
                    chart_data.append({
                        'date': date_obj,
                        'value': float(currencies[currency]),
                        'date_str': date_str
                    })
            except (ValueError, KeyError, TypeError):
                continue
        chart_data.sort(key=lambda x: x['date'])
        chart_data = chart_data[-period:]
        if not chart_data:
            ttk.Label(self.chart_frame, text=f"Нет данных по валюте {currency}").pack(expand=True)
            return
        dates = [item['date'] for item in chart_data]
        values = [item['value'] for item in chart_data]
        date_labels = [item['date_str'] for item in chart_data]

        # create chart

        fig, ax = plt.subplots(figsize=(8, 5), dpi=100)
        ax.plot(dates, values, marker='o', linestyle='-')
        ax.set_title(f"Курс {currency} к RUB за последние {len(chart_data)} дней")
        ax.set_xlabel("Дата")
        ax.set_ylabel(f"Курс ({currency}/RUB)")
        ax.grid(True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        fig.autofmt_xdate()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)


# main thread

root = tk.Tk()
app = CurrencyConverterApp(root)
root.mainloop()
