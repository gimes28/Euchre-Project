# Generated by Django 5.1.4 on 2025-01-09 20:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('homepage', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='card',
            unique_together={('suit', 'rank')},
        ),
    ]
