from django.contrib import admin
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.urls import reverse

from .models import Order, OrderItem
import datetime
from openpyxl import Workbook


def export_to_xlsx(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_disposition = f'attachment; filename={opts.verbose_name}.xlsx'
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = content_disposition
    workbook = Workbook()
    worksheet = workbook.active
    fields = [field for field in opts.get_fields() if not field.many_to_many and not field.one_to_many]

    # Записать заголовок
    field_names = [field.verbose_name for field in fields]
    worksheet.append(field_names)

    # Записать данные
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name)
            if isinstance(value, datetime.datetime):
                value = value.strftime('%d/%m/%Y')
            data_row.append(value)
        worksheet.append(data_row)

    workbook.save(response)
    return response


export_to_xlsx.short_description = 'Export to XLSX'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'email', 'address', 'postal_code', 'city', 'paid',
                    'order_stripe_payment', 'order_pdf', 'created', 'updated', 'order_detail']
    list_filter = ['paid', 'created', 'updated']
    inlines = [OrderItemInline]
    actions = [export_to_xlsx]

    def order_stripe_payment(self, obj):
        url = obj.get_stripe_url()
        if obj.stripe_id:
            html = f'<a href="{url}" target="_blank">{obj.stripe_id}</a>'
            return mark_safe(html)
        return ''

    order_stripe_payment.short_description = 'Stripe payment'

    def order_detail(self, obj):
        url = reverse('orders:admin_order_detail', args=[obj.id])
        return mark_safe(f'<a href="{url}">View</a>')

    def order_pdf(self, obj):
        url = reverse('orders:admin_order_pdf', args=[obj.id])
        return mark_safe(f'<a href="{url}">PDF</a>')

    order_pdf.short_description = 'Invoice'
