# Generated by Django 5.1.4 on 2025-02-06 03:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homepage', '0010_alter_playedcard_hand'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameresult',
            name='winner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_games', to='homepage.player'),
        ),
    ]
