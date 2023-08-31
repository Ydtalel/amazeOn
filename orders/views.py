from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.conf import settings

import os

from payment.tasks import payment_completed
from .models import OrderItem, Order
from .forms import OrderCreateForm
from cart.cart import Cart
from .tasks import order_created


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.discount
            order.save()
            for item in cart:
                OrderItem.objects.create(order=order, product=item['product'], price=item['price'],
                                         quantity=item['quantity'])
            # очистить корзину
            cart.clear()
            # запустить асинхронное задание
            order_created.delay(order.id)
            # задать заказ в сеансе
            request.session['order_id'] = order.id
            # перенаправить к платежу
            return redirect(reverse('payment:process'))
            # return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm()
        return render(request, 'orders/order/create.html', {'cart': cart, 'form': form})


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/orders/order/detail.html', {'order': order})


def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    context = {'order': order}
    html = render_to_string('orders/order/pdf.html', context)
    # Load the CSS file content
    css_file_path = os.path.join(settings.STATIC_ROOT, 'css', 'pdf.css')
    css_file_content = open(css_file_path, 'r').read()
    # Embed styles in the HTML content
    html_with_styles = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>PDF Document</title>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style>
                {css_file_content}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
    '''
    # Create a PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=order_{order.id}.pdf'
    # Generate PDF using xhtml2pdf
    pdf = pisa.CreatePDF(html_with_styles, dest=response, encoding='UTF-8')
    if not pdf.err:
        return response
    return HttpResponse('Error generating PDF', content_type='text/plain')
