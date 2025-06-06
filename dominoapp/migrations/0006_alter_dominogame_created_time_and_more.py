# Generated by Django 5.1.3 on 2025-01-14 16:40

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dominoapp', '0005_alter_dominogame_created_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dominogame',
            name='created_time',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2025, 1, 14, 16, 40, 29, 827096, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.AlterField(
            model_name='dominogame',
            name='lastTime1',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2025, 1, 14, 16, 40, 29, 827020, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.AlterField(
            model_name='dominogame',
            name='lastTime2',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2025, 1, 14, 16, 40, 29, 827033, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.AlterField(
            model_name='dominogame',
            name='lastTime3',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2025, 1, 14, 16, 40, 29, 827043, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.AlterField(
            model_name='dominogame',
            name='lastTime4',
            field=models.DateTimeField(blank=True, default=datetime.datetime(2025, 1, 14, 16, 40, 29, 827053, tzinfo=datetime.timezone.utc), null=True),
        ),
        migrations.AlterField(
            model_name='dominogame',
            name='start_time',
            field=models.DateTimeField(default=datetime.datetime(2025, 1, 14, 16, 40, 29, 826888, tzinfo=datetime.timezone.utc)),
        ),
        migrations.AlterField(
            model_name='player',
            name='lastTimeInSystem',
            field=models.DateTimeField(default=datetime.datetime(2025, 1, 14, 16, 40, 29, 826315, tzinfo=datetime.timezone.utc)),
        ),
    ]
