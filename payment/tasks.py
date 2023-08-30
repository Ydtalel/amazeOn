from io import BytesIO
from celery import shared_task
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from xhtml2pdf import pisa
from orders.models import Order


@shared_task
def payment_completed(order_id):
    """
    Задание по отправке уведомления по электронной почте
    при успешной оплате заказа.
    """
    order = Order.objects.get(id=order_id)
    # Создание объекта EmailMessage
    subject = f'Eshop – Invoice no. {order.id}'
    message = 'Please, find attached the invoice for your recent purchase.'
    from_email = settings.EMAIL_HOST_USER
    email = EmailMessage(subject, message, from_email, [order.email])
    # Генерация HTML для xhtml2pdf
    html = render_to_string('orders/order/pdf.html', {'order': order})
    pdf_file = BytesIO()
    # Создание PDF с помощью xhtml2pdf
    pisa.CreatePDF(html, dest=pdf_file)
    # Прикрепление PDF-файла
    email.attach(f'order_{order.id}.pdf', pdf_file.getvalue(), 'application/pdf')
    # Отправка электронного письма
    email.send()
