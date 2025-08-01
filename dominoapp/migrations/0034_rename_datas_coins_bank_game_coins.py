# Generated by Django 5.0.6 on 2025-08-01 14:32
from functools import partial
import django.utils.timezone
from django.db import migrations, models

def update_game_coins(apps, schema_editor, model_name):
    db_alias = schema_editor.connection.alias
    MyModel = apps.get_model('dominoapp', model_name)
    
    for obj in MyModel.objects.using(db_alias).all():
        obj.datas_coins = obj.datas_coins + obj.matches_coins
        obj.save()
class Migration(migrations.Migration):

    dependencies = [
        ('dominoapp', '0033_status_payment_alter_transaction_paymentmethod_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bank',
            name='time_created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='bank',
            options={'ordering': ['-time_created']},
        ),
        migrations.RenameField(
            model_name='bank',
            old_name='ads_coins',
            new_name='data_completed',
        ),
        migrations.RenameField(
            model_name='bank',
            old_name='created_coins',
            new_name='data_played',
        ),
        migrations.RenameField(
            model_name='bank',
            old_name='private_tables_coins',
            new_name='game_completed',
        ),
        migrations.RemoveField(
            model_name='bank',
            name='balance',
        ),
        migrations.AddField(
            model_name='bank',
            name='game_played',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='bank',
            name='promotion_coins',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(partial(update_game_coins, model_name='bank'),reverse_code=migrations.RunPython.noop),
        migrations.RenameField(
            model_name='bank',
            old_name='datas_coins',
            new_name='game_coins',
        ),
        migrations.RemoveField(
            model_name='bank',
            name='matches_coins',
        ),
    ]
