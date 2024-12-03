import tkinter as tk
import time
from typing import Literal


class Container(tk.Frame):
    """ Класс контейнера """
    def __init__(self, master, text, rel_h):
        self.width = master.width * 0.9
        self.height = master.height * rel_h
        self.max_col = 7
        # вызываем конструктор базового класса
        super().__init__(
            master=master,
            width=self.width,
            height=self.height,
            highlightbackground="black",
            highlightthickness=4,
        )
        self.label = tk.Label(master, text=text, font=('Tahoma', 15))
        self.tasks = list()
        self.frame_for_slots = tk.Frame(self)
        self.slots: [TaskSlot] = []

    def restruct_slots(self, slots_count):
        """ Пересоздает слоты """
        self.slots = [
            TaskSlot(self.frame_for_slots) for _ in range(slots_count)
        ]
        for slave in self.frame_for_slots.grid_slaves():
            slave.grid_forget()
        self.place()

    def add_slot(self):
        """ Добавляет новый слот """
        self.slots.append(TaskSlot(self.frame_for_slots))
        return self.slots[-1]

    def update_grid(self):
        """ Обновляет расположение слотов """
        for slave in self.frame_for_slots.grid_slaves():
            slave.grid_forget()
        for i, slot in enumerate(self.slots):
            slot.grid(column=i % self.max_col, row=i // 7 * self.max_col,
                      pady=10, padx=10)

    def fill_with_tasks(self):
        """ Заполняет слоты задачами """
        self.tasks = []
        for i, slot in enumerate(self.slots, start=1):
            task = Task(master=slot, title=f'Task #{i}')
            task.update()
            slot.task = task
            self.tasks.append(task)
            task.place(anchor=tk.CENTER,
                       relx=.5, rely=.5,
                       width=task.width - 2, height=task.height - 2)

    def place(self, *args, **kwargs):
        super().place(*args, **kwargs)
        if 'rely' in kwargs:
            kwargs['rely'] -= .03
        self.label.place(*args, **kwargs)
        self.frame_for_slots.place(anchor=tk.CENTER, relx=0.5, rely=0.5)
        for i, slot in enumerate(self.slots):
            slot.grid(column=i % self.max_col, row=i // 7 * self.max_col, pady=10, padx=10)


class WorkField(tk.Frame):
    """
    Рабочая зона на экране
    именно тут располагаются потоки и слоты
    """
    def __init__(self, master, rel_width):
        self.width = master.winfo_screenwidth() * rel_width
        self.height = master.winfo_screenheight()
        # вызываем конструктор базового класса
        super().__init__(
            master=master,
            width=self.width,
            height=self.height,
            highlightbackground="gray",
            highlightthickness=1,
        )
        self.pending_container = Container(self, "Pending", rel_h=0.3)
        self.in_progress_container = Container(self, "In progress", rel_h=0.19)
        self.result_container = Container(self, "Finished", rel_h=0.3)

    def set_start_position(self, config_field):
        """
        Выставляет стартовую позицию элементов
        на экране после нажатия кнопки 'start'
        """
        self.pending_container.restruct_slots(
            int(config_field.task_count.get().split()[0])
        )
        self.pending_container.fill_with_tasks()
        self.in_progress_container.restruct_slots(
            int(config_field.thread_count.get().split()[0])
        )
        self.result_container.restruct_slots(0)

    def fill_threads(self):
        """ task pending -> in_progress """
        k = 0
        for i, slot_in_progress in enumerate(self.in_progress_container.slots):
            if i - k >= len(self.pending_container.slots):
                break
            task = self.pending_container.slots[i - k].task
            self.pending_container.slots.pop(i - k).grid_forget()
            k += 1
            slot_in_progress.task = Task(
                slot_in_progress, title=task.title, status='in_progress'
            )
            slot_in_progress.task.place(
                anchor=tk.CENTER,
                relx=.5, rely=.5,
                width=task.width - 2, height=task.height - 2
            )

    def move_from_pending_to_in_progress(self, in_progress_slot):
        """ task pending -> in_progress only one task """
        if not self.pending_container.slots:
            return
        pending_slot = self.pending_container.slots.pop(0)
        pending_task = pending_slot.task
        self.pending_container.update_grid()
        in_progress_slot.task = Task(
            in_progress_slot, title=pending_task.title, status='in_progress'
        )
        in_progress_slot.task.place(
            anchor=tk.CENTER,
            relx=.5, rely=.5,
            width=pending_task.width - 2, height=pending_task.height - 2
        )

    def move_from_in_progress_to_completed(self, in_progress_slot):
        """ in_progress -> completed """
        task = in_progress_slot.task
        task.place_forget()
        in_progress_slot.task = None
        new_slot = self.result_container.add_slot()
        new_task = Task(new_slot, title=task.title, status='completed')
        new_task.complete_percent = 100
        new_slot.task = new_task
        self.result_container.update_grid()
        self.result_container.tasks.append(new_task)
        new_slot.task.place(
            anchor=tk.CENTER,
            relx=.5, rely=.5,
            width=task.width - 2, height=task.height - 2
        )
        new_slot.task.update()

    def start_job(self, win):
        """Главный цикл работы """
        while (all(slot.task for slot in self.in_progress_container.slots) or
               all(slot.task for slot in self.pending_container.slots)):
            win.update()
            for slot_in_progress in self.in_progress_container.slots:
                if slot_in_progress.task is None:
                    continue
                if slot_in_progress.task.complete_percent == 100:
                    # положить вниз
                    self.move_from_in_progress_to_completed(slot_in_progress)
                    # взять сверху, если есть
                    self.move_from_pending_to_in_progress(slot_in_progress)
                slot_in_progress.task.work(win)
                if slot_in_progress.task.complete_percent == 100:
                    # положить вниз
                    self.move_from_in_progress_to_completed(slot_in_progress)
                    # взять сверху, если есть
                    self.move_from_pending_to_in_progress(slot_in_progress)

    def place(self, *args, **kwargs):
        super().place(*args, **kwargs)
        self.pending_container.place(rely=0.03, relx=0.01)
        self.in_progress_container.place(rely=0.37, relx=0.01)
        self.result_container.place(rely=0.6, relx=0.01)


class TaskSlot(tk.Frame):
    """
    Класс слотов для задач
    используется также как поток
    """
    def __init__(self, master):
        self.width = master.master.master.width / 10
        self.height = master.master.master.height / 10
        # вызываем конструктор базового класса
        super().__init__(
            master,
            width=self.width, height=self.height,
            highlightthickness=3, highlightbackground="black"
        )
        self.task = None


class Task(tk.Label):
    """ Класс задачи """
    def __init__(self, master, title, status: Literal['pending', 'in_progress', 'completed'] = 'pending'):
        self.width = master.width
        self.height = master.height
        # вызываем конструктор базового класса
        super().__init__(
            master=master,
            text=f'{title}\n0%',
            font=('Tahoma', 15)
        )
        self['bg'] = '#eaedf2'
        self.title = title
        self.complete_percent = 0
        self.status = status

    def update(self):
        """Обновляет цвет задачи и значение процента выполнения"""
        self['text'] = f'{self.title}\n{self.complete_percent}%'
        match self.status:
            case 'pending': self['bg'] = '#eaedf2'
            case 'in_progress': self['bg'] = '#89cef0'
            case 'completed': self['bg'] = '#c9e9d1'

    def work(self, win):
        """ Непосредственно сама работа """
        self.status = 'in_progress'
        for i in range(10):
            if self.complete_percent < 100:
                self.complete_percent += 1
            else:
                self.status = 'completed'
            # искусственная временная задержка
            time.sleep(0.01)
            self.update()
            win.update()

        self.status = 'pending'
        self.update()
        win.update()


class ConfigField(tk.Frame):
    """
    Зона конфигураций на экране,
    именно тут мы можем выбрать количество потоков и задач
    """
    def __init__(self, master, rel_width):
        # вызываем конструктор базового класса
        super().__init__(
            master=master,
            height=master.winfo_screenheight(),
            width=master.winfo_screenwidth() * rel_width,
            highlightbackground="gray",
            highlightthickness=1,
        )
        self.title = tk.Label(self, text="Options", font=("Tahoma", 25))
        self.start_btn = tk.Button(self, text="Start", font=("Tahoma", 15))
        self.thread_options = [
            (str(i) + (" thread" if i == 1 else " threads")).ljust(13)
            for i in range(1, 8)
        ]
        self.task_options = [
            (str(i) + (" task" if i == 1 else " tasks")).ljust(13)
            for i in range(1, 15)
        ]
        self.thread_count = tk.StringVar(self)
        self.thread_count.set(self.thread_options[0])
        self.task_count = tk.StringVar(self)
        self.task_count.set(self.task_options[0])
        self.threads_dropdown = tk.OptionMenu(self, self.thread_count, *self.thread_options)
        self.threads_dropdown.config(font=('Tahoma', 18))
        self.tasks_dropdown = tk.OptionMenu(self, self.task_count, *self.task_options)
        self.tasks_dropdown.config(font=('Tahoma', 18))

    def place(self, *args, **kwargs):
        super().place(*args, **kwargs)
        self.title.place(anchor=tk.CENTER, relx=0.5, rely=0.35)
        self.tasks_dropdown.place(anchor=tk.E, relx=0.5, rely=0.4)
        self.threads_dropdown.place(anchor=tk.W, relx=0.5, rely=0.4)
        self.start_btn.place(anchor=tk.CENTER, relx=0.5, rely=0.45)


class Win(tk.Tk):
    """ Класс графичекого окна приложения """
    def __init__(self, *args, **kwargs):
        # вызываем конструктор базового класса
        super().__init__(*args, **kwargs)
        self.attributes('-zoomed', True)
        self.title('Threadings')


class App:
    """ Главный класс приложения """
    def __init__(self):
        self.win = Win()
        rel_width = 0.30
        self.config_field = ConfigField(self.win, rel_width)
        self.work_field = WorkField(self.win, 1 - rel_width)
        self.config_field.start_btn['command'] = self.start

    def place_widgets(self):
        """ Располагает виджеты на экране """
        self.config_field.place(anchor=tk.NE, relx=1)
        self.work_field.place(anchor=tk.NW, x=0)

    def start(self):
        """ Срабатывает после нажатия кнопки 'старт' """
        # выставляет начальную позицию всех задач
        self.work_field.set_start_position(self.config_field)
        self.win.update()
        # секундная задержка
        time.sleep(1)
        # заполняет потоки задачами, которые находятся в ожидании
        self.work_field.fill_threads()
        self.win.update()
        # запускаем работу потоков
        self.work_field.start_job(self.win)

    def run(self):
        """ Запускает приложение """
        self.place_widgets()
        self.win.mainloop()


if __name__ == '__main__':
    app = App()
    app.run()