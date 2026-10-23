import uuid
from tkinter.constants import CASCADE

from django.db import models
from django.db.models.fields import CharField
from django.forms import DateTimeField


class Train(models.Model):
    train_name=models.CharField(max_length=200)
    train_number=models.IntegerField(unique=True)
    source=models.CharField(max_length=200)
    destination=models.CharField(max_length=200)
    departure_time=models.TimeField()
    arrival_time=models.TimeField()
    total_ac_seats = models.IntegerField()
    total_non_ac_seats = models.IntegerField()
    non_ac_price=models.DecimalField(max_digits=10, decimal_places=2,default=1)
    ac_price=models.DecimalField(max_digits=10, decimal_places=2,default=1)
class Schedule(models.Model):
    train=models.ForeignKey(Train,on_delete=models.CASCADE,related_name="schedules")
    travel_date = models.DateField()
    booked_ac_seats = models.IntegerField(default=0)
    booked_non_ac_seats = models.IntegerField(default=0)
class Passenger(models.Model):
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10,choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=10, null=True, blank=True,unique=True)
class Ticket(models.Model):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="tickets")
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name="tickets")
    seat_type = models.CharField(max_length=10, choices=[("AC", "AC"), ("NON-AC", "Non-AC")])
    status = models.CharField(max_length=20, choices=[("CONFIRMED", "Confirmed"), ("WAITING", "Waiting")])
    booking_time = models.DateTimeField(auto_now_add=True)
    updated_time = models.DateTimeField(auto_now=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    seat_number = models.CharField(max_length=10, null=True, blank=True)
class Payment(models.Model):
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name="payment")
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=(("PAID", "Paid"), ("REFUNDED", "Refunded")),
        default="PAID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    refunded_at = models.DateTimeField(blank=True, null=True)
class ManagementAccount(models.Model):
    passenger_name = models.CharField(max_length=200)
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="entries")
    transaction_id = models.UUIDField(unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("PAID", "PAID"), ("REFUNDED", "REFUNDED")])
    created_at = models.DateTimeField(auto_now_add=True)
    refunded_at = models.DateTimeField(blank=True, null=True)
class Report_bal(models.Model):
    mgmt_id= models.CharField(max_length=20, unique=True)
    name=models.CharField(max_length=100)
    paid_stus=models.CharField(max_length=200,choices=[("PAID","PAID")])
    refunded_stus=models.CharField(max_length=200,choices=[("REFUNDED","REFUNDED")])
    seat_no=models.CharField(max_length=200)
    amount=models.BigIntegerField()
    paid_date=models.DateTimeField(auto_now_add=True,blank=True,null=True)
    refunded_date=models.DateTimeField(blank=True,null=True,auto_now_add=True)
    opening_bal=models.BigIntegerField()
    credit=models.BigIntegerField()
    debit=models.BigIntegerField()
    closing_bal=models.BigIntegerField()