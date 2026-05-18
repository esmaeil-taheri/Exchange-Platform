from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exchange', '0015_rename_reject_reson_wallet_reject_reason'),
    ]

    operations = [
        migrations.RenameField(
            model_name='currency',
            old_name='maintance_fee',
            new_name='maintenance_fee',
        ),
    ]
