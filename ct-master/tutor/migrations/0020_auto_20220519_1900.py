

from django.db import migrations


def remove_sector(apps, schema_editor):
    Sector = apps.get_model("tutor", "Sector")
    Sector.objects.filter(display="Professional").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('tutor', '0019_alter_issue_type'),
    ]

    operations = [
         migrations.RunPython(remove_sector)
    ]
