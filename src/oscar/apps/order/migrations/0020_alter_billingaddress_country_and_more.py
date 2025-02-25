# Generated by Django 5.1.4 on 2025-02-23 11:58

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0010_abstractaddress_country_alter_useraddress_country'),
        ('order', '0019_alter_billingaddress_line4_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingaddress',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='address.country', verbose_name='Country'),
        ),
        migrations.AlterField(
            model_name='shippingaddress',
            name='country',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='address.country', verbose_name='Country'),
        ),
    ]
