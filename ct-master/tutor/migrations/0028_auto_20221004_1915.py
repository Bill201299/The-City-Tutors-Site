# Generated by Django 3.2.5 on 2022-10-04 23:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0027_auto_20220912_0100'),
    ]

    operations = [
        migrations.AddField(
            model_name='livesession',
            name='trainer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tutor.profile'),
        ),
        migrations.AlterField(
            model_name='livesession',
            name='q1',
            field=models.TextField(blank=True, null=True, verbose_name='What do you see as the role of the tutor? How do you see yourself as a tutor?'),
        ),
        migrations.AlterField(
            model_name='livesession',
            name='q2',
            field=models.TextField(blank=True, null=True, verbose_name='Recall the module: Ethics and Professionalism. Identify 3-4 characteristics, elements, or key points you took from that module'),
        ),
    ]