from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0014_transaction_card'),
    ]

    operations = [
        migrations.RenameField(
            model_name='wallet',
            old_name='reject_reson',
            new_name='reject_reason',
        ),
    ]
