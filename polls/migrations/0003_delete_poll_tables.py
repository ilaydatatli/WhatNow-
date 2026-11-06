# Drops the old poll tables (Phase 5). Once applied to the live database, the whole
# `polls` app can be deleted (CLAUDE.md section 8).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("polls", "0002_alter_poll_author_alter_poll_created_at"),
    ]

    operations = [
        # Children first so foreign keys never point at a missing table.
        migrations.DeleteModel(name="Vote"),
        migrations.DeleteModel(name="Option"),
        migrations.DeleteModel(name="Poll"),
    ]
