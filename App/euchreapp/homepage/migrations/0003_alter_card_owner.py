# Generated by Django 5.1.4 on 2025-04-07 22:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homepage', '0002_card_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='card',
            name='owner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cards', to='homepage.player'),
        ),
    ]
