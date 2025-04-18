# Generated by Django 5.1.4 on 2025-01-28 07:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('homepage', '0008_alter_playedcard_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playedcard',
            name='hand',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='played_cards', to='homepage.hand'),
            preserve_default=False,
        ),
    ]
