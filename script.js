class Calendar {
    constructor() {
        this.currentDate = new Date();
        this.selectedDate = null;
        this.events = this.loadEvents();
        this.init();
    }

    init() {
        this.renderCalendar();
        this.setupEventListeners();
        this.updateEventsPanel();
    }

    setupEventListeners() {
        document.getElementById('prevMonth').addEventListener('click', () => {
            this.currentDate.setMonth(this.currentDate.getMonth() - 1);
            this.renderCalendar();
        });

        document.getElementById('nextMonth').addEventListener('click', () => {
            this.currentDate.setMonth(this.currentDate.getMonth() + 1);
            this.renderCalendar();
        });

        document.getElementById('todayBtn').addEventListener('click', () => {
            this.currentDate = new Date();
            this.selectedDate = new Date();
            this.renderCalendar();
            this.updateEventsPanel();
        });

        document.getElementById('addEventBtn').addEventListener('click', () => {
            this.addEvent();
        });

        document.getElementById('eventInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.addEvent();
            }
        });
    }

    renderCalendar() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();
        
        // Обновляем заголовок
        const monthNames = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ];
        document.getElementById('currentMonthYear').textContent = 
            `${monthNames[month]} ${year}`;

        // Получаем первый день месяца и количество дней
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();
        
        // Корректируем день недели (воскресенье = 0, но нам нужно чтобы было 6)
        const adjustedStartingDay = startingDayOfWeek === 0 ? 6 : startingDayOfWeek - 1;

        const calendarGrid = document.getElementById('calendarGrid');
        calendarGrid.innerHTML = '';

        // Заголовки дней недели
        const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
        dayNames.forEach(day => {
            const dayHeader = document.createElement('div');
            dayHeader.className = 'day-header';
            dayHeader.textContent = day;
            calendarGrid.appendChild(dayHeader);
        });

        // Дни предыдущего месяца
        const prevMonthLastDay = new Date(year, month, 0).getDate();
        for (let i = adjustedStartingDay - 1; i >= 0; i--) {
            const day = prevMonthLastDay - i;
            this.createDayCell(day, year, month - 1, true);
        }

        // Дни текущего месяца
        for (let day = 1; day <= daysInMonth; day++) {
            this.createDayCell(day, year, month, false);
        }

        // Дни следующего месяца
        const totalCells = calendarGrid.children.length - 7; // минус заголовки
        const remainingCells = 42 - totalCells; // 6 недель * 7 дней
        for (let day = 1; day <= remainingCells; day++) {
            this.createDayCell(day, year, month + 1, true);
        }
    }

    createDayCell(day, year, month, isOtherMonth) {
        const cell = document.createElement('div');
        cell.className = 'day-cell';
        
        if (isOtherMonth) {
            cell.classList.add('other-month');
        }

        const cellDate = new Date(year, month, day);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        cellDate.setHours(0, 0, 0, 0);

        // Проверяем, является ли день сегодняшним
        if (cellDate.getTime() === today.getTime() && !isOtherMonth) {
            cell.classList.add('today');
        }

        // Проверяем, является ли день выбранным
        if (this.selectedDate) {
            const selected = new Date(this.selectedDate);
            selected.setHours(0, 0, 0, 0);
            if (cellDate.getTime() === selected.getTime() && !isOtherMonth) {
                cell.classList.add('selected');
            }
        }

        const dayNumber = document.createElement('div');
        dayNumber.className = 'day-number';
        dayNumber.textContent = day;
        cell.appendChild(dayNumber);

        // Показываем количество событий
        const dateKey = this.getDateKey(cellDate);
        const dayEvents = this.events[dateKey] || [];
        if (dayEvents.length > 0) {
            const eventsIndicator = document.createElement('div');
            eventsIndicator.className = 'day-events';
            eventsIndicator.textContent = `${dayEvents.length} событий`;
            cell.appendChild(eventsIndicator);
        }

        // Обработчик клика
        if (!isOtherMonth) {
            cell.addEventListener('click', () => {
                this.selectedDate = new Date(year, month, day);
                this.renderCalendar();
                this.updateEventsPanel();
            });
        }

        document.getElementById('calendarGrid').appendChild(cell);
    }

    updateEventsPanel() {
        if (!this.selectedDate) {
            this.selectedDate = new Date();
        }

        const dateKey = this.getDateKey(this.selectedDate);
        const dateEvents = this.events[dateKey] || [];

        // Обновляем заголовок
        const dateStr = this.selectedDate.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric'
        });
        document.getElementById('selectedDate').textContent = dateStr;

        // Обновляем список событий
        const eventsList = document.getElementById('eventsList');
        eventsList.innerHTML = '';

        if (dateEvents.length === 0) {
            eventsList.innerHTML = '<div class="empty-events">Нет событий на этот день</div>';
        } else {
            dateEvents.forEach((event, index) => {
                const eventItem = document.createElement('div');
                eventItem.className = 'event-item';
                eventItem.innerHTML = `
                    <span class="event-text">${event}</span>
                    <button class="delete-btn" data-index="${index}">Удалить</button>
                `;
                
                eventItem.querySelector('.delete-btn').addEventListener('click', () => {
                    this.deleteEvent(dateKey, index);
                });
                
                eventsList.appendChild(eventItem);
            });
        }
    }

    addEvent() {
        const input = document.getElementById('eventInput');
        const eventText = input.value.trim();

        if (!eventText) return;

        if (!this.selectedDate) {
            this.selectedDate = new Date();
        }

        const dateKey = this.getDateKey(this.selectedDate);
        
        if (!this.events[dateKey]) {
            this.events[dateKey] = [];
        }

        this.events[dateKey].push(eventText);
        this.saveEvents();
        
        input.value = '';
        this.renderCalendar();
        this.updateEventsPanel();
    }

    deleteEvent(dateKey, index) {
        if (this.events[dateKey]) {
            this.events[dateKey].splice(index, 1);
            if (this.events[dateKey].length === 0) {
                delete this.events[dateKey];
            }
            this.saveEvents();
            this.renderCalendar();
            this.updateEventsPanel();
        }
    }

    getDateKey(date) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }

    loadEvents() {
        const stored = localStorage.getItem('calendarEvents');
        return stored ? JSON.parse(stored) : {};
    }

    saveEvents() {
        localStorage.setItem('calendarEvents', JSON.stringify(this.events));
    }
}

// Инициализация календаря при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new Calendar();
});
