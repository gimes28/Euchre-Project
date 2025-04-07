# Generated by Django 5.1.4 on 2025-04-07 11:53

import django.db.models.deletion
import homepage.bot_logic
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('trump_suit', models.CharField(blank=True, choices=[('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')], max_length=10, null=True)),
                ('team1_points', models.IntegerField(default=0)),
                ('team2_points', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('is_human', models.BooleanField(default=False)),
                ('team', models.IntegerField(default=0)),
                ('partner', models.CharField(default='', max_length=100)),
            ],
            bases=(models.Model, homepage.bot_logic.BotLogic),
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('suit', models.CharField(choices=[('hearts', 'Hearts'), ('diamonds', 'Diamonds'), ('clubs', 'Clubs'), ('spades', 'Spades')], max_length=10)),
                ('rank', models.CharField(choices=[('9', '9'), ('10', '10'), ('J', 'Jack'), ('Q', 'Queen'), ('K', 'King'), ('A', 'Ace')], max_length=5)),
                ('is_trump', models.BooleanField(default=False)),
            ],
            options={
                'unique_together': {('suit', 'rank')},
            },
        ),
        migrations.CreateModel(
            name='Hand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trick_number', models.IntegerField(default=0)),
                ('trump_suit', models.CharField(max_length=20)),
                ('starting_player', models.CharField(default='', max_length=100)),
                ('current_trick', models.IntegerField(default=1)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='hands', to='homepage.game')),
                ('dealer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hands_dealt', to='homepage.player')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='hands_won', to='homepage.player')),
            ],
        ),
        migrations.CreateModel(
            name='PlayedCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=0)),
                ('trick_number', models.IntegerField(default=1)),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homepage.card')),
                ('hand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='homepage.hand')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homepage.player')),
            ],
        ),
        migrations.CreateModel(
            name='GameResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_hands', models.IntegerField()),
                ('points', models.JSONField()),
                ('game', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='homepage.game')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='won_games', to='homepage.player')),
            ],
        ),
        migrations.AddField(
            model_name='game',
            name='dealer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='games_as_dealer', to='homepage.player'),
        ),
        migrations.CreateModel(
            name='Trick',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trick_number', models.PositiveIntegerField()),
                ('hand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tricks', to='homepage.hand')),
                ('winner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tricks_won', to='homepage.player')),
            ],
        ),
        migrations.CreateModel(
            name='TrickPlay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('play_order', models.PositiveIntegerField()),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homepage.card')),
                ('player', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homepage.player')),
                ('trick', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='homepage.trick')),
            ],
        ),
        migrations.AddField(
            model_name='trick',
            name='players',
            field=models.ManyToManyField(related_name='tricks_played', through='homepage.TrickPlay', to='homepage.player'),
        ),
    ]
