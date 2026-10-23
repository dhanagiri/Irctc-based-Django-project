from django.urls import path
from .views import *
urlpatterns=[
    path("train_create",train_creating,name="create"),
    path("train_listing",train_list,name="listtrain"),
    path("ticket_book",ticket_booking,name="booking"),
    path("ticket_cancel",ticket_cancellation,name="ticketcancel"),
    path("ticket_reports",ticket_report,name="ticketreport"),
    # path("managereport",manage_report,name="managreport"),
    path("payment",payment_report,name="report"),
    path("every_train_ticrep",train_ticket_report,name="everytrain "),
    path("apiapi",payment_step),
    # path("balance_tb_api",balance_table)
]
