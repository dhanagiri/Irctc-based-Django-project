import decimal
import io
from datetime import datetime, date , timedelta,timezone
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.db.models.aggregates import Count
from django.views.decorators.csrf import csrf_exempt

from .models import *
from django.http import HttpResponse,JsonResponse
import json
from django.db import transaction
from django.utils.timezone import now
from django.utils import timezone
from django.core.paginator import Paginator
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill






@csrf_exempt
def train_creating(request):
    if request.method=="POST":
        data=json.loads(request.body)
        if isinstance(data, dict):
            data = [data]
        try:
            for i in data:
                Train.objects.create(
                    train_name=i["train_name"],
                    train_number=i["train_number"],
                    source=i["source"],
                    destination=i["destination"],
                    departure_time=i["departure_time"],
                    arrival_time=i["arrival_time"],
                    total_ac_seats=i["total_ac_seats"],
                    total_non_ac_seats=i["total_non_ac_seats"],
                    ac_price=i["ac_price"],
                    non_ac_price=i["non_ac_price"]
                )
                id_=Train.objects.get(train_number=i["train_number"])
                Schedule.objects.create(
                    train=id_,
                    travel_date=date.today() + timedelta(days=1),
                    booked_ac_seats=i["booked_ac_seats"],
                    booked_non_ac_seats=i["booked_non_ac_seats"]
                )
                return HttpResponse("Success")
        except Exception as e:
            return HttpResponse(json.dumps({"Invalid Details": str(e), "line_no": str(e.__traceback__.tb_lineno)}), content_type='application/json')
    return JsonResponse({"error":"Post method only required"})
@csrf_exempt
def train_list(request):
        source = request.GET.get("source")
        destination = request.GET.get("destination")
        date_str = request.GET.get("date")
        if not source or not destination:
            return JsonResponse("error:Source and destination required")
        if not date_str:
            travel_date = date.today()
        else:
            try:
                travel_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse("error: Invalid date format. Use YYYY-MM-DD")
        if travel_date < date.today():
            return JsonResponse({"error": "No trains available for past dates"})
        schedu = Schedule.objects.filter(
            train__source__iexact=source.strip(),
            train__destination__iexact=destination.strip(),
            # travel_date=travel_date
        )
        if travel_date == date.today():
            current_time = now().time()
            schedu = schedu.filter(train__departure_time__gte=current_time)
        data = []
        for s in schedu:
            total_seats = s.train.total_ac_seats + s.train.total_non_ac_seats
            available_ac = s.train.total_ac_seats - s.booked_ac_seats
            available_non_ac = s.train.total_non_ac_seats - s.booked_non_ac_seats
            available_total = available_ac + available_non_ac
            if available_ac > 0:
                status_ac=f"Available seats-{available_ac}"
            else:
                status_ac="No Available seats"
            if available_non_ac > 0:
                status_non_ac = f"Available seats-{available_non_ac}"
            else:
                status_non_ac = "No Available seats"
            data.append({
                "schedule_id":s.id,
                "train_number": s.train.train_number,
                "train_name": s.train.train_name,
                "source": s.train.source,
                "destination": s.train.destination,
                "departure_time": s.train.departure_time.strftime("%I:%M %p"),
                "arrival_time": s.train.arrival_time.strftime("%I:%M %p"),
                "total_seats": total_seats,
                "total_ac_seats": s.train.total_ac_seats,
                "total_non_ac_seats": s.train.total_non_ac_seats,
                "available_ac_seats": available_ac,
                "available_non_ac_seats": available_non_ac,
                "available_total_seats": available_total,
                "status_ac": status_ac,
                "status_non_ac": status_non_ac,
                "ac_price":s.train.ac_price,
                "non_ac_price":s.train.non_ac_price,
                "travel_date":s.travel_date
            })
        return JsonResponse(data, safe=False)
@csrf_exempt
def ticket_booking(request):
    if request.method != "POST":
        return HttpResponse("POST method only required")
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse("error :Invalid JSON payload")
    schedule_id = data.get("schedule_id")
    if not isinstance(schedule_id, int):
        return JsonResponse("error: Invalid or missing schedule_id")
    seat_type = data.get("seat_type", "NON-AC").upper()
    if seat_type not in ["AC", "NON-AC"]:
        return JsonResponse({"error": "Invalid 'seat_type'. Must be 'AC' or 'NON-AC'"})
    try:
        amount = Decimal(data.get("amount", "0"))
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        return JsonResponse({"error": "Invalid 'amount'"})
    passenger_data = data.get("passenger")
    if not isinstance(passenger_data, dict):
        return JsonResponse("error:Missing or invalid 'passenger' data")
    required_fields = ["name", "age", "gender", "email", "phone"]
    missing_fields = [field for field in required_fields if field not in passenger_data]
    if missing_fields:
        return JsonResponse({"error": f"Missing passenger fields: {', '.join(missing_fields)}"})
    if not (isinstance(passenger_data.get("name"), str) and passenger_data["name"].strip() and passenger_data["name"].replace(" ", "").isalpha()):
        return JsonResponse({"error": "Invalid name"})
    if not isinstance(passenger_data["age"], int) or passenger_data["age"] <= 0:
        return JsonResponse({"error": "Invalid 'age'"})
    if passenger_data["gender"] not in ["M", "F", "O"]:
        return JsonResponse("error: Gender must be 'M', 'F', or 'O'",safe=False)
    if "@" not in passenger_data.get("email", "") or "." not in passenger_data["email"].split("@")[-1]:
        return JsonResponse({"error": "Invalid email format"})
    phone = passenger_data["phone"]
    if not (phone.isdigit() and len(phone) == 10):
        return JsonResponse("error:Phone number must be 10 digits",safe=False)

    try:
        with transaction.atomic():
            schedule = Schedule.objects.select_for_update().get(id=schedule_id)
            now = datetime.now()
            departure_dt = datetime.combine(schedule.travel_date, schedule.train.departure_time)
            print(departure_dt)
            cutoff = departure_dt - timedelta(days=1)
            print(cutoff)
            if now > cutoff:
                return JsonResponse({
                    "error": "Booking closed",
                    "details": f"Booking allowed only until {cutoff.strftime('%Y-%m-%d %I:%M %p')}"
                })
            expected_amount = schedule.train.ac_price if seat_type == "AC" else schedule.train.non_ac_price
            if amount != expected_amount:
                return JsonResponse({
                    "error": "Payment mismatch",
                    "details": f"Expected ₹{expected_amount}, received ₹{amount}"})
            seat_number = None
            if seat_type == "AC":
                available = schedule.train.total_ac_seats - schedule.booked_ac_seats
                if available > 0:
                    status = "CONFIRMED"
                    schedule.booked_ac_seats += 1
                    seat_number = f"AC-{schedule.booked_ac_seats}"
                else:
                    status = "WAITING"
            else:
                available = schedule.train.total_non_ac_seats - schedule.booked_non_ac_seats
                if available > 0:
                    status = "CONFIRMED"
                    schedule.booked_non_ac_seats += 1
                    seat_number = f"NAC-{schedule.booked_non_ac_seats}"
                else:
                    status = "WAITING"
            try:
                passenger = Passenger.objects.create(**passenger_data)
            except Exception as e:
                return JsonResponse({"error": "Invalid passenger data", "details": str(e)})
            schedule.save()
            ticket = Ticket.objects.create(
                schedule=schedule,
                passenger=passenger,
                seat_type=seat_type,
                status=status,
                seat_number=seat_number,
                amount=amount
            )
            payment = Payment.objects.create(ticket=ticket, amount=amount, status="PAID")
            ManagementAccount.objects.create(
                passenger_name=passenger.name,
                ticket=ticket,
                transaction_id=payment.transaction_id,
                amount=payment.amount,
                status="PAID"
            )
    except Schedule.DoesNotExist:
        return JsonResponse({"error": "Invalid schedule"})
    receipt_text = f"""
    TRAIN TICKET RECEIPT
    -----------------------------------
    Ticket ID     : {ticket.id}
    Passenger     : {passenger.name} ({passenger.gender}, {passenger.age})
    From          : {schedule.train.source}
    To            : {schedule.train.destination}
    Train         : {schedule.train.train_name}
    Seat          : {ticket.seat_number or "Not Assigned"} ({ticket.seat_type})
    Status        : {ticket.status}
    Amount Paid   : ₹{ticket.amount}
    Booking Time  : {ticket.booking_time.strftime('%Y-%m-%d %H:%M:%S')}
    -----------------------------------
    Thank you for booking with IRCTC!
    """
    response = HttpResponse(receipt_text, content_type="text/plain")
    response['Content-Disposition'] = f'attachment; filename="ticket{ticket.id}.pdf"'
    return response
@csrf_exempt
def ticket_cancellation(request):
        if request.method != "POST":
            return HttpResponse("POST method only required")
        try:
            data = json.loads(request.body)
            ticketid = data.get("ticketid")
            with transaction.atomic():
                ticket = Ticket.objects.select_for_update().get(id=ticketid)
                if ticket.status == "CANCELLED":
                    return JsonResponse({"error": "Ticket already cancelled"})
                was_confirmed = (ticket.status == "CONFIRMED")
                ticket.status = "CANCELLED"
                ticket.cancelled_time = timezone.now()
                ticket.save()
                now = timezone.now()
                refund_status = "NO_REFUND"
                payment = getattr(ticket, "payment", None)
                if (now - ticket.booking_time) <= timedelta(hours=1) and payment and payment.status == "PAID":
                    payment.status = "REFUNDED"
                    payment.refunded_at = timezone.now()
                    payment.save(update_fields=["status", "refunded_at"])
                    mgmt = ManagementAccount.objects.select_for_update().get(transaction_id=payment.transaction_id)
                    mgmt.status = "REFUNDED"
                    mgmt.refunded_at = timezone.now()
                    mgmt.save(update_fields=["status", "refunded_at"])
                    refund_status = "REFUNDED"
                    print("Payment refunded_at:", payment.refunded_at)
                    print("Mgmt refunded_at:", mgmt.refunded_at)
                promoted = None
                if was_confirmed:
                    sched = Schedule.objects.select_for_update().get(id=ticket.schedule.id)
                    if ticket.seat_type == "AC" and sched.booked_ac_seats > 0:
                        sched.booked_ac_seats -= 1
                    elif ticket.seat_type == "NON-AC" and sched.booked_non_ac_seats > 0:
                        sched.booked_non_ac_seats -= 1
                    sched.save()
                    waiting_ticket = (Ticket.objects.select_for_update().filter(schedule=ticket.schedule,seat_type=ticket.seat_type,status="WAITING").order_by("booking_time").first())
                    if waiting_ticket:
                        waiting_ticket.status = "CONFIRMED"
                        waiting_ticket.seat_number = ticket.seat_number or waiting_ticket.seat_number
                        waiting_ticket.save()
                        promoted = {
                            "ticket_id": waiting_ticket.id,
                            "passenger": waiting_ticket.passenger.name,
                            "seat_number": waiting_ticket.seat_number,}
                        sched = Schedule.objects.select_for_update().get(id=ticket.schedule.id)
                        if ticket.seat_type == "AC" and sched.booked_ac_seats > 0:
                            sched.booked_ac_seats += 1
                        elif ticket.seat_type == "NON-AC" and sched.booked_non_ac_seats > 0:
                            sched.booked_non_ac_seats += 1
                        sched.save()
        except Ticket.DoesNotExist:
            return JsonResponse({"error": "Invalid ticket ID"})
        return JsonResponse({"message": "Ticket cancelled",
            "ticket_id": ticket.id,
            "refund": refund_status,
            "promoted_waiting": promoted,})

@csrf_exempt
def ticket_report(request):
    if request.method !="POST":
        return HttpResponse("POST method require")
    download_excel = request.GET.get("download_excel", "false").lower() == "true"
    try:
        page_size=int(request.GET.get("page_size"))
        pgno=int(request.GET.get("pgno"))
    except (TypeError, ValueError):
        return JsonResponse("error:Invalid or missing pagination parameters")
    tic=Ticket.objects.values("id", "passenger__name", "schedule__train__train_name", "seat_number", "status")
    pg_data = Paginator(tic, page_size)
    try:
        pg_obj=pg_data.page(pgno)
    except Exception :
        return JsonResponse({"error": "Page out of range","total_pages": pg_data.num_pages})
    if download_excel:
        data_write= pd.DataFrame(tic)#(pg_obj.object_list)
        data_write.rename(columns={
            "id": "Ticket ID",
            "passenger__name": "Passenger Name",
            "schedule__train__train_name": "Train Name",
            "seat_number": "Seat Number",
            "status": "Status"
        }, inplace=True)
        buffer=BytesIO()
        with pd.ExcelWriter(buffer,engine="openpyxl")as writer:
                data_write.to_excel(writer,sheet_name=f"Page {pgno}", index=False)
        buffer.seek(0)
        response = HttpResponse(buffer,content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = "attachment; filename=tickets_report.xlsx"
        return response
    paginated_data = list(pg_obj.object_list)

    return JsonResponse({
        "page": pgno,
        "page_size": page_size,
        "total_pages": pg_data.num_pages,
        "total_records": pg_data.count,
        "tickets": paginated_data
    })
# @csrf_exempt
# def manage_report(request):
#     if request.method !="POST":
#           return HttpResponse("POST method only allows")
#     file=request.GET.get("file" ,"report")
#     transactions = ManagementAccount.objects.select_related("ticket").all()
#     data = []
#     for t in transactions:
#             data.append({
#                 'ID': t.id,
#                 'Passenger Name': t.passenger_name,
#                 'Status': t.status,
#                 'Ticket ID': t.ticket.id if t.ticket else None,
#                 'Amount': float(t.amount),
#                 'Created At': t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
#                 'Refunded At': t.refunded_at.strftime('%Y-%m-%d %H:%M:%S') if t.refunded_at else ''
#             })
#     print(data)
#     df = pd.DataFrame(data)
#     total_paid = ManagementAccount.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
#     total_refunded = ManagementAccount.objects.filter(status='REFUNDED').aggregate(total=Sum('amount'))['total'] or 0
#     summary_df = pd.DataFrame([
#             {'Passenger Name': '--- Summary ---'},
#         {'Passenger Name': 'Total Amount', 'Amount': total_paid + total_refunded},
#         {'Passenger Name': 'Total Paid', 'Amount': total_paid},
#         {'Passenger Name': 'Total Refunded', 'Amount': total_refunded}
#         ])
#     final_df = pd.concat([df, pd.DataFrame([{}]), summary_df], ignore_index=True)
#     response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#     response['Content-Disposition'] = f'attachment; filename={file}.xlsx'
#     with pd.ExcelWriter(response, engine='openpyxl') as writer:
#             final_df.to_excel(writer, sheet_name='Transaction Report', index=False)
#     return response
@csrf_exempt
def payment_report(request):
    if request.method != "POST":
        return HttpResponse("POST method only allows")
    file = request.GET.get("file", "report")
    try:
        query = ManagementAccount.objects.select_related("ticket__passenger").all().order_by("created_at")
        rows = []
        closing_balance = 0
        for i, p in enumerate(query, start=1):
            passenger = getattr(p.ticket.passenger, "name", "") if p.ticket else ""
            # ticket_id = p.ticket.id if p.ticket else None
            # created_at = p.created_at.strftime("%Y-%m-%d %H:%M:%S")
            # refunded_at = p.refunded_at.strftime("%Y-%m-%d %H:%M:%S") if p.refunded_at else ""
            ob = closing_balance
            cr = dr = 0
            refunded_status = "-"
            # cr, dr = 0, 0
            # if p.status == "PAID":
            #     cr = p.amount
            #     closing_balance = ob + cr
            # elif p.status == "REFUNDED":
            #     dr = p.amount
            #     closing_balance = ob
            if p.status in["PAID","REFUNDED"]:
                paid_status = "PAID"
                cr = p.amount
                closing_balance += cr
            if p.status == "REFUNDED":
                refunded_status = "REFUNDED"
                dr = p.amount
            cb = closing_balance
            rows.append({
                "ID": i,
                "Passenger Name": passenger,
                # "Status": p.status,
                "PAID Status": paid_status,
                "REFUNDED Status": refunded_status,
                "Ticket ID": p.ticket.id if p.ticket else None,
                "Amount": p.amount,
                "Created At": p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Refunded At": p.refunded_at.strftime("%Y-%m-%d %H:%M:%S") if p.refunded_at else "",
                "ob": ob,
                "cr": cr,
                "dr": dr,
                "cb": closing_balance,})
        data= pd.DataFrame(rows)
        summary_df = pd.DataFrame([
            {'Passenger Name': '--- Summary ---'},
            {'Passenger Name': 'Closing Amount', 'Amount': closing_balance},
        ])
        final_df = pd.concat([data, pd.DataFrame([{}]), summary_df], ignore_index=True)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            final_df.to_excel(writer, index=False, sheet_name="Payment Report")
        buffer.seek(0)
        response = HttpResponse(buffer,content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename={file}.xlsx'
        return response
    except Exception as e:
        return HttpResponse(json.dumps({ "error":str(e),"line_number":str(e.__traceback__.tb_lineno)}))
@csrf_exempt
def train_ticket_report(request):
    if request.method != "POST":
        return HttpResponse("Post method only allows")
    try:
        train_num = int(request.GET.get("train_num"))
        train = Train.objects.get(train_number=train_num)
        schedules = Schedule.objects.filter(train=train).annotate(
            # booked_ac=Count("tickets", filter=Q(tickets__seat_type="AC")),
            # booked_non_ac=Count("tickets", filter=Q(tickets__seat_type="NON-AC")),
            confirmed_tickets=Count("tickets", filter=Q(tickets__status="CONFIRMED")),
            waiting_tickets=Count("tickets", filter=Q(tickets__status="WAITING")),
            canceled_tickets=Count("tickets", filter=Q(tickets__status="CANCELLED"))
        )
        tic_rep  = []
        for i in schedules:
            tickets = Ticket.objects.filter(schedule=i).select_related("passenger")
            for j in tickets:
                tic_rep .append({
                    # "Train Name": train.train_name,
                    # "Train Number": train.train_number,
                    # "Source": train.source,
                    # "Destination": train.destination,
                    # "Travel Date": i.travel_date,
                    "Ticket ID": j.id,
                    "Passenger Name": j.passenger.name,
                    "Passenger Age": j.passenger.age,
                    "Passenger Gender": j.passenger.gender,
                    "Seat Type": j.seat_type,
                    "Seat Number": j.seat_number,
                    "Status": j.status,
                    "Amount": float(j.amount),
                    "Booking Time": j.booking_time.strftime("%Y-%m-%d %H:%M:%S"),
                })
        if not tic_rep :
            return JsonResponse({"message": "No tickets found for this train"})
        # data = pd.DataFrame(rows)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            train_report=pd.DataFrame([{
                "Train Name": train.train_name,
                "Train Number": train.train_number,
                "Source": train.source,
                "Destination": train.destination,
                "Travel Date": i.travel_date,
                "Total AC Seats": train.total_ac_seats,
                "Total Non-AC Seats": train.total_non_ac_seats,
                "Booked AC": i.booked_ac_seats,
                "Booked Non-AC": i.booked_non_ac_seats,
                "Available AC Seats": train.total_ac_seats- i.booked_ac_seats,
                "Available Non-AC Seats": train.total_non_ac_seats-i.booked_non_ac_seats,
                "Waiting Tickets": i.waiting_tickets,
                "Confirmed Tickets": i.confirmed_tickets,
                "Cancelled Tickets":i.canceled_tickets
            }])
            train_report.T.to_excel(writer, sheet_name="Train Report", index=True,header=False,startrow=0)
            tic_rep = pd.DataFrame(tic_rep )
            tic_rep .to_excel(writer, sheet_name="Ticket Report", index=False, startrow=0)
        buffer.seek(0)
        response = HttpResponse(
            buffer,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="train_ticket_report_{train.train_number}.xlsx"'
        return response
    except Train.DoesNotExist:
        return JsonResponse({"error": "Train not found"})
    except Exception as e:
        return JsonResponse({"error": str(e)})
@csrf_exempt
def payment_step(request):
        if request.method != "POST":
            return HttpResponse("POST method only allows")
        file=request.GET.get("file","report")
        try:
            query = (
                ManagementAccount.objects
                .select_related("ticket__passenger")
                .all()
                .order_by("created_at")
            )
            rows = []
            closing_balance = 0
            serial = 1
            for p in query:
                passenger = p.ticket.passenger.name if p.ticket and p.ticket.passenger else "-"
                ob = closing_balance
                # cr =
                dr = 0
                # paid_status =
                refunded_status = "-"
                if p.status == "PAID":
                    cr = float(p.amount)
                    closing_balance += cr
                    paid_status = "PAID"
                    rows.append({
                        "S.No": serial,
                        "Name": passenger,
                        "Paid Status": paid_status,
                        "Refunded Status": refunded_status,
                        "Seat Number": p.ticket.seat_number or "-",
                        "Amount": float(p.amount),
                        "Paid Date": p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "Refunded Date": "-",
                        "OB": ob,
                        "CR": cr,
                        "DR": dr,
                        "Closing": closing_balance
                    })
                    if not Report_bal.objects.filter(mgmt_id=f"{serial}_P").exists():
                        Report_bal.objects.create(
                            mgmt_id=f"{serial}_P",
                            name=passenger,
                            paid_stus=paid_status,
                            refunded_stus=refunded_status,
                            seat_no=p.ticket.seat_number or "-",
                            amount=float(p.amount),
                            paid_date=p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            refunded_date=None,
                            opening_bal=ob,
                            credit=cr,
                            debit=dr,
                            closing_bal=closing_balance)
                    serial += 1
                elif p.status == "REFUNDED":
                    cr = float(p.amount)
                    closing_balance += cr
                    rows.append({
                        "S.No": serial,
                        "Name": passenger,
                        "Paid Status": "PAID",
                        "Refunded Status": "-",
                        "Seat Number": p.ticket.seat_number or "-",
                        "Amount": float(p.amount),
                        "Paid Date": p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "Refunded Date": "-",
                        "OB": ob,
                        "CR": cr,
                        "DR": 0,
                        "Closing": closing_balance
                    })
                    if not Report_bal.objects.filter(mgmt_id=f"{serial}_P").exists():
                        Report_bal.objects.create(
                            mgmt_id=f"{serial}_P",
                            name=passenger,
                            paid_stus="PAID",
                            refunded_stus="-",
                            seat_no=p.ticket.seat_number or "-",
                            amount=float(p.amount),
                            paid_date=p.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                            refunded_date=None,
                            opening_bal=ob,
                            credit=cr,
                            debit=0,
                            closing_bal=closing_balance)
                    # serial += 1
                    refunded_status = "REFUNDED"
                    dr = float(p.amount)
                    closing_balance -= dr
                    rows.append({
                        "S.No": serial,
                        "Name": passenger,
                        "Paid Status": "-",
                        "Refunded Status": refunded_status,
                        "Seat Number": p.ticket.seat_number or "-",
                        "Amount": float(p.amount),
                        "Paid Date": "-",
                        "Refunded Date": (
                            p.refunded_at.strftime("%Y-%m-%d %H:%M:%S")
                            if p.refunded_at else "-"
                        ),
                        "OB": ob + cr,
                        "CR": 0,
                        "DR": dr,
                        "Closing": closing_balance
                    })
                    if not Report_bal.objects.filter(mgmt_id=f"{serial}_R").exists():
                        Report_bal.objects.create(
                            mgmt_id=f"{serial}_R",
                            name=passenger,
                            paid_stus="-",
                            refunded_stus=refunded_status,
                            seat_no=p.ticket.seat_number or "-",
                            amount= float(p.amount),
                            paid_date=None,
                            refunded_date= p.refunded_at.strftime("%Y-%m-%d %H:%M:%S")
                                if p.refunded_at else None,
                            opening_bal=ob + cr,
                            credit=0,
                            debit=dr,
                            closing_bal= closing_balance)
                    serial += 1
            data = pd.DataFrame(rows)
            summary_df = pd.DataFrame([
                {'Refunded Status': '--- Summary ---'},
                {'Refunded Status': 'Closing Amount', 'Seat Number': closing_balance},
            ])
            final_df = pd.concat([data, pd.DataFrame([{}]), summary_df], ignore_index=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                final_df.to_excel(writer, index=False, sheet_name="Payment_Report")
            output.seek(0)
            response = HttpResponse(output,content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Content-Disposition"] = f'attachment; filename={file}.xlsx'
            return response
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}")

# def balance_table(request):

