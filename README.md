# IRCTC-based Django Project

A train ticket booking backend built with Python and Django.

## Features
- Add trains with schedules, seat counts and AC / Non-AC prices
- Search trains by source, destination and date, with live seat availability
- Book tickets with passenger validation and payment amount check
- Booking closes 1 day before departure
- Overbooking prevention using database transactions and row locking
- Waiting list with automatic promotion when a ticket is cancelled
- Ticket cancellation with refund if cancelled within 1 hour
- Text receipt download after booking
- Paginated ticket report (JSON) with Excel export
- Payment report in Excel with opening, credit, debit and closing balance
- Train-wise Excel report with schedule summary and ticket details

## Tech Stack
Python, Django, Django ORM, Pandas, OpenPyXL

## API Endpoints
| Purpose | Method |
|---|---|
| Create train | POST |
| Search trains | GET (source, destination, date) |
| Book ticket | POST (JSON body) |
| Cancel ticket | POST (ticketid) |
| Ticket report | POST (pgno, page_size, download_excel) |
| Payment report | POST |
| Train ticket report | POST (train_num) |

## How to run
1. Clone the repo
2. Install dependencies: `pip install django pandas openpyxl`
3. Run migrations: `python manage.py migrate`
4. Start the server: `python manage.py runserver`
